{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "cd /home/user/qse-pkg && echo '--- QSE auto-test ---' && python3 -m pytest tests/test_graph_metrics.py -q --tb=short 2>&1 | tail -10"
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(python3 -m pytest*)",
      "Bash(python3 -m qse*)",
      "Bash(python3 scripts/*)",
      "Bash(git commit*)",
      "Bash(git push*)",
      "Bash(git tag*)",
      "Bash(git checkout*)",
      "Bash(git merge*)"
    ]
  }
}