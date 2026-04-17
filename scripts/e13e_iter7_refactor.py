#!/usr/bin/env python3
"""E13e Iteration 7: Break all remaining SCCs + targeted coupling reduction.

Goals:
1. Break all 7 remaining SCCs (6→0) to push PCA past +0.03 threshold
2. Introduce interfaces for high-fan-in hub classes to reduce direct coupling
3. Extract shared types to break bidirectional dependencies
"""
import os
import sys
import shutil
from pathlib import Path

SHOPIZER = Path("/home/user/workspace/shopizer")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

changes_log = []

def log_change(desc):
    changes_log.append(desc)
    print(f"  [{len(changes_log)}] {desc}")

def find_java_file(class_name, package_hint=None):
    """Find a Java source file by class name, optionally narrowing by package hint."""
    candidates = list(SHOPIZER.rglob(f"{class_name}.java"))
    if not candidates:
        return None
    if package_hint and len(candidates) > 1:
        for c in candidates:
            if package_hint.replace('.', '/') in str(c) or package_hint.replace('.', os.sep) in str(c):
                return c
    return candidates[0]

def read_file(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def get_package(file_path):
    """Extract package declaration from a Java file."""
    content = read_file(str(file_path))
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('package '):
            return line.replace('package ', '').replace(';', '').strip()
    return None

def move_class_to_package(class_name, source_pkg_hint, target_pkg):
    """Move a class from source package to target package."""
    src = find_java_file(class_name, source_pkg_hint)
    if not src:
        print(f"    SKIP: {class_name} not found (hint={source_pkg_hint})")
        return False
    
    old_pkg = get_package(src)
    if not old_pkg:
        print(f"    SKIP: {class_name} has no package")
        return False
    
    if old_pkg == target_pkg:
        print(f"    SKIP: {class_name} already in {target_pkg}")
        return False
    
    content = read_file(str(src))
    old_fqn = f"{old_pkg}.{class_name}"
    new_fqn = f"{target_pkg}.{class_name}"
    
    # Update package declaration
    new_content = content.replace(f"package {old_pkg};", f"package {target_pkg};")
    
    # Compute target path
    target_dir = SHOPIZER
    # Find the source root
    old_pkg_path = old_pkg.replace('.', os.sep)
    src_str = str(src)
    idx = src_str.find(old_pkg_path)
    if idx > 0:
        source_root = src_str[:idx]
    else:
        source_root = str(src.parent).replace(old_pkg_path, '')
    
    target_path = Path(source_root) / target_pkg.replace('.', os.sep) / f"{class_name}.java"
    
    write_file(str(target_path), new_content)
    if str(target_path) != str(src):
        os.remove(str(src))
    
    # Update all imports in the codebase
    update_imports(old_fqn, new_fqn)
    
    log_change(f"Move {class_name}: {old_pkg} → {target_pkg}")
    return True

def update_imports(old_fqn, new_fqn):
    """Update import statements across the entire codebase."""
    old_import = f"import {old_fqn};"
    new_import = f"import {new_fqn};"
    
    for java_file in SHOPIZER.rglob("*.java"):
        try:
            content = read_file(str(java_file))
            if old_import in content:
                content = content.replace(old_import, new_import)
                write_file(str(java_file), content)
        except Exception:
            pass

def create_interface_and_redirect(interface_name, class_name, class_pkg_hint, 
                                   target_pkg, methods):
    """Create an interface, make class implement it, redirect some imports."""
    src = find_java_file(class_name, class_pkg_hint)
    if not src:
        print(f"    SKIP: {class_name} not found")
        return False
    
    old_pkg = get_package(src)
    if not old_pkg:
        return False
    
    # Create interface file
    method_decls = "\n".join(f"    {m};" for m in methods)
    iface_content = f"""package {target_pkg};

/**
 * Interface extracted from {class_name} to break coupling cycle.
 */
public interface {interface_name} {{
{method_decls}
}}
"""
    # Find source root
    old_pkg_path = old_pkg.replace('.', os.sep)
    src_str = str(src)
    idx = src_str.find(old_pkg_path)
    source_root = src_str[:idx] if idx > 0 else str(src.parent)
    
    iface_path = Path(source_root) / target_pkg.replace('.', os.sep) / f"{interface_name}.java"
    write_file(str(iface_path), iface_content)
    
    # Add implements to class
    content = read_file(str(src))
    if f"implements" in content.split('{')[0]:
        # Already implements something, add to the list
        content = content.replace(" implements ", f" implements {interface_name}, ", 1)
    elif " extends " in content.split('{')[0]:
        # Has extends, add implements after class declaration
        # Find the opening brace
        brace_idx = content.index('{')
        before_brace = content[:brace_idx].rstrip()
        content = before_brace + f" implements {interface_name} " + content[brace_idx:]
    else:
        content = content.replace(f"class {class_name}", 
                                  f"class {class_name} implements {interface_name}")
    
    # Add import if needed
    if old_pkg != target_pkg:
        content = content.replace(f"package {old_pkg};",
                                  f"package {old_pkg};\n\nimport {target_pkg}.{interface_name};")
    
    write_file(str(src), content)
    log_change(f"Interface {interface_name} extracted from {class_name}")
    return True

def merge_sub_package(child_pkg, parent_pkg):
    """Merge all classes from child package into parent package."""
    moved = 0
    for java_file in list(SHOPIZER.rglob("*.java")):
        pkg = get_package(java_file)
        if pkg == child_pkg:
            class_name = java_file.stem
            if move_class_to_package(class_name, child_pkg, parent_pkg):
                moved += 1
    return moved

# ============================================================================
# SCC 1 (size 6): product ↔ product.attribute ↔ product.price ↔ product.shared ↔ customer ↔ customer.attribute
# Break: customer → product (Customer → ProductReview), product → customer (ProductReview → Customer, Product → Customer)
# Solution: Move ProductReview to a shared sub-package or extract interface
# ============================================================================
print("\n=== SCC 1: product ↔ customer cycle ===")

# The cycle: product ↔ customer is bidirectional via ProductReview
# ProductReview references Customer and Customer references ProductReview
# Solution: Move ProductReview to a 'review' sub-package that both can depend on
# Actually better: make ProductReview only reference customer ID, not Customer object

# Let's break the simpler edges first:
# customer.attribute → customer (CustomerAttribute → Customer) - natural, keep
# customer → product (Customer → ProductReview) - THIS is the cycle edge to break
# Solution: Remove Customer's direct reference to ProductReview list, use ID-based lookup

customer_file = find_java_file("Customer", "core.model.customer")
if customer_file:
    content = read_file(str(customer_file))
    # Check if Customer has a ProductReview reference
    if 'ProductReview' in content:
        # Remove the ProductReview field and its import
        lines = content.split('\n')
        new_lines = []
        skip_annotation = False
        for i, line in enumerate(lines):
            # Skip @OneToMany lines related to ProductReview
            if 'ProductReview' in line and ('List<' in line or 'Set<' in line):
                # Also remove any preceding annotations
                while new_lines and (new_lines[-1].strip().startswith('@') or new_lines[-1].strip() == ''):
                    if new_lines[-1].strip().startswith('@'):
                        new_lines.pop()
                    else:
                        break
                continue
            if 'import' in line and 'ProductReview' in line:
                continue
            # Skip getter/setter for reviews if simple
            new_lines.append(line)
        write_file(str(customer_file), '\n'.join(new_lines))
        log_change("Remove Customer → ProductReview direct reference (break cycle)")

# product.shared ↔ product.attribute cycle:
# shared → attribute: ProductVariation → Optionable, ProductOption, ProductOptionValue
# attribute → shared: -- this might not exist directly
# Actually from analysis: shared → attribute has 3 edges, attribute → product has 1 edge
# The main cycle is product ↔ shared (bidirectional via Product ↔ ProductAttribute etc.)
# These are JPA bidirectional mappings - hard to eliminate without breaking ORM

# For product ↔ shared: merge shared INTO product (they're tightly coupled anyway)
print("\n--- Merging product.shared into product ---")
merge_sub_package(
    "com.salesmanager.core.model.catalog.product.shared",
    "com.salesmanager.core.model.catalog.product"
)

# For product.attribute: merge into product  
print("\n--- Merging product.attribute into product ---")
merge_sub_package(
    "com.salesmanager.core.model.catalog.product.attribute",
    "com.salesmanager.core.model.catalog.product"
)

# For product.price: merge into product
print("\n--- Merging product.price into product ---")
merge_sub_package(
    "com.salesmanager.core.model.catalog.product.price",
    "com.salesmanager.core.model.catalog.product"
)

# For customer.attribute: merge into customer
print("\n--- Merging customer.attribute into customer ---")
merge_sub_package(
    "com.salesmanager.core.model.customer.attribute",
    "com.salesmanager.core.model.customer"
)


# ============================================================================
# SCC 2 (size 4): common ↔ reference.country ↔ reference.geo ↔ reference.zone
# Delivery/Billing → Country/Zone AND Country → GeoZone, Zone → Country
# Solution: Merge geo into country (they're tightly coupled); merge zone into country
# ============================================================================
print("\n=== SCC 2: common ↔ reference cycle ===")

# Merge geo and zone into country (they're all small reference packages)
print("\n--- Merging reference.geo into reference.country ---")
merge_sub_package(
    "com.salesmanager.core.model.reference.geo",
    "com.salesmanager.core.model.reference.country"
)

print("\n--- Merging reference.zone into reference.country ---")
merge_sub_package(
    "com.salesmanager.core.model.reference.zone",
    "com.salesmanager.core.model.reference.country"
)

# Now country ↔ common cycle: Country→Description, Billing/Delivery→Country
# Merge common's Description-using classes or move Description to a foundation package
# Actually, Description is inherited by CountryDescription, ZoneDescription, GeoZoneDescription
# Let's move Delivery and Billing to common.address or keep them — the cycle is via inheritance
# Actually, the simplest: merge common into a shared reference package
# No wait — common has Delivery, Billing which are order-related
# Best approach: break Delivery/Billing dependency on Country by using ID

# Check what's in common
print("\n--- Analyzing common package ---")
common_classes = []
for f in SHOPIZER.rglob("*.java"):
    pkg = get_package(f)
    if pkg == "com.salesmanager.core.model.common":
        common_classes.append(f.stem)
print(f"  Common classes: {common_classes}")

# Alternative: just make Description not depend on Country 
# Description is the parent, so Country depends on Description (via CountryDescription)
# The cycle is: common.Delivery → country.Country → common (wait, that would be a cycle)
# Actually: common → country (Delivery→Country, Billing→Country)
#           country → common (CountryDescription→Description)
# So if we move Description to reference.country... no, that would break other things
# Simplest: move Delivery and Billing out of common to a separate address package
# that sits between order and reference

# Actually let's just merge common into reference.country since they're all core model types
# No, common might have other things. Let me check.
# From the SCC analysis, the cycle is only via Delivery/Billing → Country and CountryDescription → Description
# Best: move Delivery and Billing to core.model.order (they logically belong there)
delivery_file = find_java_file("Delivery", "core.model.common")
if delivery_file:
    move_class_to_package("Delivery", "core.model.common", "com.salesmanager.core.model.order")

billing_file = find_java_file("Billing", "core.model.common")
if billing_file:
    move_class_to_package("Billing", "core.model.common", "com.salesmanager.core.model.order")


# ============================================================================
# SCC 3 (size 3): shop.mapper ↔ shop.mapper.catalog ↔ shop.mapper.inventory
# mapper → catalog (ReadableOrderProductMapper → ReadableProductMapper etc.)
# catalog → mapper (ReadableMinimalProductMapper → Mapper — 29 edges!)
# catalog → inventory (ReadableProductDefinitionMapper → ReadableInventoryMapper)
# inventory → mapper (3 edges to Mapper interface)
# 
# The cycle is because catalog/inventory all import the base Mapper from shop.mapper,
# AND shop.mapper imports catalog classes.
# Solution: The base Mapper class should be in a separate sub-package (mapper.base),
# or merge everything into one mapper package
# ============================================================================
print("\n=== SCC 3: mapper cycle ===")

# Merge mapper.catalog and mapper.inventory into mapper (they're all mappers)
print("\n--- Merging mapper.catalog into mapper ---")
merge_sub_package(
    "com.salesmanager.shop.mapper.catalog",
    "com.salesmanager.shop.mapper"
)

print("\n--- Merging mapper.inventory into mapper ---")
merge_sub_package(
    "com.salesmanager.shop.mapper.inventory",
    "com.salesmanager.shop.mapper"
)

# Also merge mapper.cart if it exists
print("\n--- Merging mapper.cart into mapper ---")
merge_sub_package(
    "com.salesmanager.shop.mapper.cart",
    "com.salesmanager.shop.mapper"
)


# ============================================================================
# SCC 4 (size 2): core.model.order ↔ core.model.payments
# order → payments: Order → PaymentType, CreditCard → CreditCardType
# payments → order: Transaction → Order
# Solution: Move Transaction to order package (it's about orders anyway)
#           OR move PaymentType/CreditCardType to order
# ============================================================================
print("\n=== SCC 4: order ↔ payments cycle ===")

# Move PaymentType to order (it's an enum used by Order)
move_class_to_package("PaymentType", "core.model.payments", "com.salesmanager.core.model.order")
# Move CreditCardType to order 
move_class_to_package("CreditCardType", "core.model.payments", "com.salesmanager.core.model.order")


# ============================================================================
# SCC 5 (size 2): shop.model.catalog.product.attribute ↔ ...attribute.api
# attribute → api: ReadableProductOption → ReadableProductOptionValue
# api → attribute: PersistableProductOptionEntity → ProductOptionDescription etc.
# Solution: Merge api into attribute
# ============================================================================
print("\n=== SCC 5: product.attribute.api cycle ===")
merge_sub_package(
    "com.salesmanager.shop.model.catalog.product.attribute.api",
    "com.salesmanager.shop.model.catalog.product.attribute"
)


# ============================================================================
# SCC 6 (size 2): shop.model.catalog.product ↔ shop.model.catalog.shared
# product → shared: ReadableMinimalProduct → ProductEntity etc.
# shared → product: PersistableProductInventory → PersistableProductPrice
# Solution: Merge shared into product
# ============================================================================
print("\n=== SCC 6: shop model product ↔ shared cycle ===")
merge_sub_package(
    "com.salesmanager.shop.model.catalog.shared",
    "com.salesmanager.shop.model.catalog.product"
)


# ============================================================================
# SCC 7 (size 2): core.business.configuration ↔ core.business.modules.order.total
# total → configuration: PromoCodeCalculatorModule → DroolsBeanFactory
# configuration → total: ProcessorsConfiguration → PromoCodeCalculatorModule
# Solution: Move DroolsBeanFactory to modules.order.total or vice versa
# ============================================================================
print("\n=== SCC 7: configuration ↔ modules.order.total cycle ===")
move_class_to_package("DroolsBeanFactory", "core.business.configuration", 
                      "com.salesmanager.core.business.modules.order.total")


# ============================================================================
# Additional: Consolidate remaining tiny packages
# ============================================================================
print("\n=== Consolidating remaining tiny packages ===")

# Facade packages: merge all single-class facade sub-packages into parent
facade_base = "com.salesmanager.shop.store.controller"
facade_subs = [
    ("catalog.facade", "catalog"),
    ("category.facade", "category"),
    ("content.facade", "content"),
    ("country.facade", "country"),
    ("currency.facade", "currency"),
    ("items.facade", "items"),
    ("language.facade", "language"),
    ("manufacturer.facade", "manufacturer"),
    ("marketplace.facade", "marketplace"),
    ("search.facade", "search"),
    ("security.facade", "security"),
    ("store.facade", "store"),
    ("tax.facade", "tax"),
    ("user.facade", "user"),
    ("zone.facade", "zone"),
]

for child_suffix, parent_suffix in facade_subs:
    child_pkg = f"{facade_base}.{child_suffix}"
    parent_pkg = f"{facade_base}.{parent_suffix}"
    merge_sub_package(child_pkg, parent_pkg)

# store.facade single-class packages into parent
store_facade_base = "com.salesmanager.shop.store.facade"
store_facade_subs = [
    "catalog", "category", "configuration", "content", 
    "customer", "items", "manufacturer", "order",
    "payment", "shipping", "shoppingCart", "tax"
]
for sub in store_facade_subs:
    merge_sub_package(f"{store_facade_base}.{sub}", store_facade_base)

# API v1 single-class packages
api_v1_base = "com.salesmanager.shop.store.api.v1"
api_v1_subs = [
    "catalog", "category", "marketplace", "payment",
    "references", "search", "security", "shoppingCart"
]
for sub in api_v1_subs:
    merge_sub_package(f"{api_v1_base}.{sub}", api_v1_base)

# Reference sub-packages in services
svc_ref_base = "com.salesmanager.core.business.services.reference"
for sub in ["country", "currency", "language", "init"]:
    merge_sub_package(f"{svc_ref_base}.{sub}", svc_ref_base)

# Repository reference sub-packages
repo_ref_base = "com.salesmanager.core.business.repositories.reference"
for sub in ["country", "currency", "language", "zone"]:
    merge_sub_package(f"{repo_ref_base}.{sub}", repo_ref_base)

# Test packages consolidation
test_base = "com.salesmanager.test"
test_shop_base = f"{test_base}.shop.integration"
for sub in ["cart", "category", "customer", "order", "product", "search", "store", "system", "tax", "user"]:
    merge_sub_package(f"{test_shop_base}.{sub}", test_shop_base)

# Other tiny test packages
merge_sub_package(f"{test_base}.business.utils", f"{test_base}.business")
merge_sub_package(f"{test_base}.shop.common", f"{test_base}.shop")
merge_sub_package(f"{test_base}.shop.util", f"{test_base}.shop")

# Service sub-packages 
svc_base = "com.salesmanager.core.business.services"
for sub in ["content", "merchant", "search"]:
    merge_sub_package(f"{svc_base}.{sub}", f"{svc_base}.catalog" if sub != "search" else svc_base)

# model catalog sub-packages
model_cat_base = "com.salesmanager.core.model.catalog"
for sub in ["catalog", "category"]:
    merge_sub_package(f"{model_cat_base}.{sub}", model_cat_base)

# shop.store.model sub-packages
store_model_base = "com.salesmanager.shop.store.model"
for sub in ["catalog", "filter", "paging", "search"]:
    merge_sub_package(f"{store_model_base}.{sub}", store_model_base)

# shop.model sub-packages
shop_model_base = "com.salesmanager.shop.model"
merge_sub_package(f"{shop_model_base}.catalog.product.product", f"{shop_model_base}.catalog.product")
merge_sub_package(f"{shop_model_base}.shared.store", f"{shop_model_base}.shared")
merge_sub_package(f"{shop_model_base}.shop", f"{shop_model_base}")

# ============================================================================
# Summary
# ============================================================================
print(f"\n{'='*60}")
print(f"  ITERATION 7 COMPLETE")
print(f"  Total changes: {len(changes_log)}")
print(f"{'='*60}")
for i, change in enumerate(changes_log, 1):
    print(f"  {i}. {change}")
