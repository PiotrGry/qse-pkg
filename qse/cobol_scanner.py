"""
COBOL AGQ Scanner — prototype
Oblicza M/A/S/C z grafu zależności COBOL (CALL + COPY).
Kompatybilny z AGQ v1.0: wagi (0.20, 0.20, 0.55, 0.05).

Obsługuje: .cbl, .cob, .CBL, .COB (fixed + free format)
Dependency types: CALL (control flow), COPY (data coupling)
"""
import re, json
import numpy as np
import networkx as nx
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


def parse_cobol_file(filepath: Path) -> dict:
    """Ekstrahuje PROGRAM-ID, CALL i COPY z pliku COBOL."""
    text = filepath.read_text(errors='ignore')
    lines = text.splitlines()

    # Strip sequence numbers (fixed format COBOL: cols 1-6 = seq, 7 = indicator)
    code_lines = []
    for line in lines:
        if len(line) > 6:
            indicator = line[6]
            if indicator == '*' or indicator == '/':
                continue  # comment
            code = line[6:72].strip() if len(line) >= 72 else line[6:].strip()
            code_lines.append(code)
        else:
            code_lines.append(line.strip())

    full_text = ' '.join(code_lines).upper()

    # PROGRAM-ID
    m = re.search(r'PROGRAM-ID\.\s+(\S+?)[\.\s]', full_text)
    program_id = m.group(1).rstrip('.') if m else filepath.stem.upper()

    # CALL statements (static: 'PROGNAME' or "PROGNAME")
    calls  = re.findall(r"\bCALL\s+'(\w+)'", full_text)
    calls += re.findall(r'\bCALL\s+"(\w+)"', full_text)

    # COPY statements (copybook dependencies = data coupling)
    copies = re.findall(r'\bCOPY\s+(\w+)', full_text)

    # PERFORM statements (internal structure / cohesion proxy)
    performs = re.findall(r'\bPERFORM\s+(\w[\w-]*)', full_text)
    skip = {'VARYING','UNTIL','THRU','THROUGH','TIMES','TEST','WITH','FOREVER','INLINE'}
    performs = [p for p in performs if p not in skip]

    # Paragraphs in PROCEDURE DIVISION
    paragraphs = re.findall(r'^(\w[\w-]*)\.\s*$', full_text, re.MULTILINE)

    loc = len([l for l in code_lines if l.strip()])

    return {
        'program_id': program_id,
        'filename':   filepath.name,
        'call_deps':  list(set(calls)),
        'copy_deps':  list(set(copies)),
        'perform_refs': list(set(performs)),
        'n_paragraphs': len(paragraphs),
        'n_performs':   len(set(performs)),
        'loc':        loc,
    }


def compute_cobol_agq(cobol_dir: str,
                      weights: Tuple[float,float,float,float] = (0.20, 0.20, 0.55, 0.05)
                      ) -> dict:
    """
    Oblicza AGQ dla systemu COBOL.

    Mapowanie komponentów:
      Modularity  ← Newman Q na grafie CALL (izolacja programów)
      Acyclicity  ← 1 - fraction nodes in CALL cycles
      Stability   ← var(Instability) / 0.25  (Martin per program)
      Cohesion    ← mean(PERFORM coverage per program)

    Dodatkowe metryki specyficzne dla COBOL:
      copy_coupling_density: gęstość grafu COPY (ryzyko propagacji zmian)
      hottest_copybook: copybook używany przez najwięcej programów
      migration_risk: per-program risk score = I * (1 + copy_coupling/10)
    """
    cobol_path = Path(cobol_dir)
    files = (list(cobol_path.rglob('*.cbl')) +
             list(cobol_path.rglob('*.CBL')) +
             list(cobol_path.rglob('*.cob')) +
             list(cobol_path.rglob('*.COB')))

    if not files:
        return {'error': f'No COBOL files found in {cobol_dir}'}

    programs = {}
    for f in files:
        p = parse_cobol_file(f)
        programs[p['program_id']] = p

    N = len(programs)
    all_ids = set(programs.keys())

    # Graf CALL (control flow)
    G_call = nx.DiGraph()
    G_call.add_nodes_from(all_ids)
    for pid, p in programs.items():
        for called in p['call_deps']:
            if called in all_ids:
                G_call.add_edge(pid, called)

    # Graf COPY (data coupling przez wspólne copybooks)
    copybook_usage: Dict[str, List[str]] = defaultdict(list)
    for pid, p in programs.items():
        for copy in p['copy_deps']:
            copybook_usage[copy].append(pid)

    G_copy = nx.DiGraph()
    G_copy.add_nodes_from(all_ids)
    for cb, users in copybook_usage.items():
        for i, u1 in enumerate(users):
            for u2 in users[i+1:]:
                G_copy.add_edge(u1, u2)
                G_copy.add_edge(u2, u1)

    # ── Modularity (CALL graph) ───────────────────────────────────
    if G_call.number_of_edges() > 0:
        try:
            U = G_call.to_undirected()
            comms = list(nx.community.greedy_modularity_communities(U))
            Q = nx.community.modularity(U, comms)
            modularity = max(0.0, min(1.0, Q / 0.75))
        except Exception:
            modularity = 0.5
    else:
        modularity = 1.0  # zero calls = perfect isolation

    # ── Acyclicity (CALL graph) ───────────────────────────────────
    cycles = list(nx.simple_cycles(G_call))
    nodes_in_cycles = set(n for c in cycles for n in c)
    acyclicity = 1.0 - len(nodes_in_cycles) / N if N > 0 else 1.0

    # ── Stability (Martin's Instability per program) ──────────────
    instabilities = []
    per_prog_risk = []
    for pid in all_ids:
        ca = G_call.in_degree(pid)
        ce = G_call.out_degree(pid)
        total = ca + ce
        I = ce / total if total > 0 else 0.5
        instabilities.append(I)
        copy_count = sum(1 for cb, users in copybook_usage.items() if pid in users)
        risk = I * (1 + copy_count / 10.0)
        per_prog_risk.append({
            'program': pid,
            'risk': round(risk, 3),
            'instability': round(I, 3),
            'ca': ca, 'ce': ce,
            'copy_coupling': copy_count,
            'loc': programs[pid]['loc'],
        })

    stability = min(1.0, np.var(instabilities) / 0.25) if len(instabilities) >= 2 else 0.5

    # ── Cohesion (PERFORM coverage) ───────────────────────────────
    coh_vals = []
    for p in programs.values():
        n_par = p['n_paragraphs']
        n_per = p['n_performs']
        if n_par > 1:
            coh_vals.append(min(n_per, n_par) / n_par)
    cohesion = float(np.mean(coh_vals)) if coh_vals else 0.5

    # ── AGQ ───────────────────────────────────────────────────────
    w = weights
    agq = w[0]*modularity + w[1]*acyclicity + w[2]*stability + w[3]*cohesion

    # Fingerprint
    if acyclicity >= 0.95 and stability > 0.7 and cohesion >= 0.4:
        fingerprint = "LAYERED"
    elif acyclicity >= 0.95 and stability > 0.7:
        fingerprint = "CLEAN"
    elif acyclicity < 0.95 and cohesion < 0.3:
        fingerprint = "TANGLED"
    elif acyclicity < 0.95:
        fingerprint = "CYCLIC"
    elif acyclicity >= 0.95 and cohesion < 0.4:
        fingerprint = "LOW_COHESION"
    elif acyclicity >= 0.95 and stability < 0.3:
        fingerprint = "FLAT"
    else:
        fingerprint = "LAYERED"

    # COPY coupling density (COBOL-specific metric)
    max_copy_edges = N * (N - 1) if N > 1 else 1
    copy_density = G_copy.number_of_edges() / max_copy_edges

    # Hottest copybook (highest propagation risk)
    hottest = sorted(copybook_usage.items(), key=lambda x: -len(x[1]))
    hottest_cb  = hottest[0][0] if hottest else None
    hottest_n   = len(hottest[0][1]) if hottest else 0

    # Migration order (sort by risk ascending = migrate low-risk first)
    migration_order = sorted(per_prog_risk, key=lambda x: x['risk'])

    return {
        'language': 'COBOL',
        'n_programs': N,
        'agq_score': round(agq, 4),
        'fingerprint': fingerprint,
        'modularity':  round(modularity,  4),
        'acyclicity':  round(acyclicity,  4),
        'stability':   round(stability,   4),
        'cohesion':    round(cohesion,    4),
        # COBOL-specific
        'cobol': {
            'n_call_edges':   G_call.number_of_edges(),
            'n_copy_edges':   G_copy.number_of_edges(),
            'n_call_cycles':  len(cycles),
            'n_copybooks':    len(copybook_usage),
            'copy_density':   round(copy_density, 4),
            'hottest_copybook': hottest_cb,
            'hottest_copybook_n_users': hottest_n,
            'copybook_usage': {k: v for k,v in
                               sorted(copybook_usage.items(), key=lambda x: -len(x[1]))[:20]},
        },
        'migration_order': migration_order,
        'programs': {pid: {
            'loc': p['loc'],
            'n_calls': len(p['call_deps']),
            'n_copies': len(p['copy_deps']),
        } for pid, p in programs.items()},
    }


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/cobol_samples/aws_carddemo/app/cbl'
    result = compute_cobol_agq(path)
    print(json.dumps(result, indent=2))
