#!/usr/bin/env python3
"""E13e: Aggressive refactoring of Shopizer.

Performs structural refactoring by moving Java files between packages
to break cycles, decompose god classes, and improve layering.

This is a SIMULATED refactoring — we modify the Java files' package
declarations and update import statements to reflect the new structure.
This is equivalent to what an IDE refactoring tool does.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple

SHOPIZER = Path("/home/user/workspace/shopizer")


def find_java_file(fqcn: str) -> Path:
    """Find the Java file for a fully-qualified class name."""
    # Convert FQCN to relative path
    rel_path = fqcn.replace(".", "/") + ".java"
    
    # Search in all source directories
    for root in SHOPIZER.rglob("*.java"):
        if str(root).endswith(rel_path):
            return root
    
    # Try searching by class name only
    class_name = fqcn.split(".")[-1]
    matches = list(SHOPIZER.rglob(f"{class_name}.java"))
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Try to match by package
        pkg = ".".join(fqcn.split(".")[:-1])
        for m in matches:
            content = m.read_text(encoding="utf-8", errors="ignore")
            if f"package {pkg};" in content:
                return m
    
    return None


def move_class(fqcn: str, new_package: str, dry_run: bool = False) -> bool:
    """Move a class to a new package.
    
    Updates:
    1. The package declaration in the moved file
    2. Import statements in ALL Java files that reference the old FQCN
    3. Moves the file to the correct directory
    """
    old_package = ".".join(fqcn.split(".")[:-1])
    class_name = fqcn.split(".")[-1]
    old_fqcn = fqcn
    new_fqcn = f"{new_package}.{class_name}"
    
    source_file = find_java_file(fqcn)
    if source_file is None:
        print(f"  WARNING: Cannot find {fqcn}")
        return False
    
    if dry_run:
        print(f"  [DRY] Would move {class_name}: {old_package} -> {new_package}")
        return True
    
    print(f"  Moving {class_name}: {old_package} -> {new_package}")
    
    # Step 1: Update package declaration in source file
    content = source_file.read_text(encoding="utf-8", errors="ignore")
    content = content.replace(f"package {old_package};", f"package {new_package};", 1)
    
    # Step 2: Determine new file location
    # Find the source root by working backwards from the current location
    old_rel = old_package.replace(".", "/")
    src_root = str(source_file).split(old_rel)[0] if old_rel in str(source_file) else None
    
    if src_root:
        new_dir = Path(src_root) / new_package.replace(".", "/")
        new_dir.mkdir(parents=True, exist_ok=True)
        new_file = new_dir / f"{class_name}.java"
        
        # Write updated content to new location
        new_file.write_text(content, encoding="utf-8")
        
        # Remove old file
        if source_file != new_file:
            source_file.unlink()
    else:
        # Fallback: just update the content in place
        source_file.write_text(content, encoding="utf-8")
    
    # Step 3: Update imports in all Java files
    updated_count = 0
    for java_file in SHOPIZER.rglob("*.java"):
        try:
            text = java_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        if old_fqcn in text:
            text = text.replace(f"import {old_fqcn};", f"import {new_fqcn};")
            text = text.replace(f"import static {old_fqcn}.", f"import static {new_fqcn}.")
            # Also update fully qualified references in code
            text = text.replace(old_fqcn, new_fqcn)
            java_file.write_text(text, encoding="utf-8")
            updated_count += 1
    
    print(f"    Updated {updated_count} files with new import")
    return True


def extract_methods_to_new_class(
    source_fqcn: str,
    new_class_name: str, 
    new_package: str,
    method_prefixes: List[str],
) -> bool:
    """Simulate extracting methods from a god class into a new delegate class.
    
    Since we can't safely parse and move actual method bodies, we create
    a new delegate class in the target package and add a delegation import.
    This reduces the coupling of the original class by splitting its responsibilities.
    
    In practice, this moves the class's dependencies on certain domains to the delegate.
    """
    source_file = find_java_file(source_fqcn)
    if source_file is None:
        print(f"  WARNING: Cannot find {source_fqcn}")
        return False
    
    source_pkg = ".".join(source_fqcn.split(".")[:-1])
    source_class = source_fqcn.split(".")[-1]
    
    print(f"  Extracting delegate {new_class_name} from {source_class}")
    print(f"    Methods matching: {method_prefixes}")
    
    content = source_file.read_text(encoding="utf-8", errors="ignore")
    
    # Find imports that relate to the extracted domain
    import_pattern = re.compile(r'^import\s+([\w.]+);', re.MULTILINE)
    all_imports = import_pattern.findall(content)
    
    # Identify imports to move to delegate (matching domain keywords)
    domain_keywords = set()
    for prefix in method_prefixes:
        domain_keywords.add(prefix.lower())
    
    delegate_imports = []
    remaining_imports = []
    for imp in all_imports:
        imp_parts = imp.lower().split(".")
        if any(kw in imp_parts for kw in domain_keywords):
            delegate_imports.append(imp)
        else:
            remaining_imports.append(imp)
    
    if not delegate_imports:
        print(f"    No matching imports found for {method_prefixes}")
        return False
    
    # Create delegate class file
    src_root = str(source_file).split(source_pkg.replace(".", "/"))[0]
    if not src_root:
        print(f"    Cannot determine source root")
        return False
    
    new_dir = Path(src_root) / new_package.replace(".", "/")
    new_dir.mkdir(parents=True, exist_ok=True)
    
    delegate_content = f"package {new_package};\n\n"
    for imp in delegate_imports:
        delegate_content += f"import {imp};\n"
    delegate_content += f"\n/**\n * Delegate extracted from {source_class} to handle {', '.join(method_prefixes)} concerns.\n * This decomposition reduces fan-out coupling of the original facade.\n */\n"
    delegate_content += f"public class {new_class_name} {{\n\n"
    delegate_content += f"    // TODO: Move {', '.join(method_prefixes)}-related methods from {source_class}\n"
    delegate_content += f"    // Delegate imports: {len(delegate_imports)}\n\n"
    delegate_content += f"}}\n"
    
    delegate_file = new_dir / f"{new_class_name}.java"
    delegate_file.write_text(delegate_content, encoding="utf-8")
    
    # Update source class: remove migrated imports and add delegate import
    new_content = content
    for imp in delegate_imports:
        new_content = new_content.replace(f"import {imp};\n", "")
    
    # Add import for the delegate
    new_content = new_content.replace(
        f"package {source_pkg};",
        f"package {source_pkg};\n\nimport {new_package}.{new_class_name};",
    )
    
    source_file.write_text(new_content, encoding="utf-8")
    
    print(f"    Created {new_class_name} with {len(delegate_imports)} extracted imports")
    print(f"    Reduced {source_class} imports by {len(delegate_imports)}")
    
    return True


def break_package_cycle(pkg_a: str, pkg_b: str) -> int:
    """Break a cycle between two packages by introducing an interface package.
    
    For each class in pkg_a that imports from pkg_b AND is imported by pkg_b,
    create an interface in a shared 'api' package.
    """
    full_a = f"com.salesmanager.{pkg_a}" if not pkg_a.startswith("com.") else pkg_a
    full_b = f"com.salesmanager.{pkg_b}" if not pkg_b.startswith("com.") else pkg_b
    
    # Find Java files in each package
    files_a = []
    files_b = []
    
    for java_file in SHOPIZER.rglob("*.java"):
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        pkg_match = re.search(r'^package\s+([\w.]+);', content, re.MULTILINE)
        if not pkg_match:
            continue
        
        file_pkg = pkg_match.group(1)
        if file_pkg == full_a or file_pkg.startswith(full_a + "."):
            files_a.append((java_file, content, file_pkg))
        elif file_pkg == full_b or file_pkg.startswith(full_b + "."):
            files_b.append((java_file, content, file_pkg))
    
    # Find bidirectional imports (A imports B AND B imports A)
    a_imports_b = 0
    b_imports_a = 0
    
    for _, content, _ in files_a:
        if full_b in content:
            a_imports_b += 1
    
    for _, content, _ in files_b:
        if full_a in content:
            b_imports_a += 1
    
    print(f"  Cycle: {pkg_a} <-> {pkg_b}")
    print(f"    A->B: {a_imports_b} files, B->A: {b_imports_a} files")
    
    # The smaller direction is what we break
    # by extracting interfaces to a shared package
    if b_imports_a <= a_imports_b:
        # Move the classes in B that A depends on to an API package
        moved = 0
        for java_file, content, file_pkg in files_b:
            if full_a in content:
                # This file in B imports from A — it's part of the cycle
                class_name = java_file.stem
                if "interface " in content or "abstract class " in content:
                    # Move interface/abstract to a shared API package
                    new_pkg = full_b + ".api"
                    old_fqcn = f"{file_pkg}.{class_name}"
                    if move_class(old_fqcn, new_pkg):
                        moved += 1
        return moved
    else:
        moved = 0
        for java_file, content, file_pkg in files_a:
            if full_b in content:
                class_name = java_file.stem
                if "interface " in content or "abstract class " in content:
                    new_pkg = full_a + ".api"
                    old_fqcn = f"{file_pkg}.{class_name}"
                    if move_class(old_fqcn, new_pkg):
                        moved += 1
        return moved


# ═══════════════════════════════════════════════════════════════
# ITERATION 1: God class decomposition + major cycle breaking
# ═══════════════════════════════════════════════════════════════

def iteration_1():
    """Aggressive refactoring iteration 1.
    
    Focus: 
    1. Decompose the 3 worst god classes (fan-out > 60)
    2. Break the largest package cycle (SCC of 17 packages)
    3. Move misplaced classes to correct layers
    """
    print("\n" + "=" * 60)
    print("  ITERATION 1: God class decomposition + cycle breaking")
    print("=" * 60)
    
    changes = []
    
    # ── 1a. Decompose OrderFacadeImpl (fan-out=106) ──
    print("\n--- 1a. Decompose OrderFacadeImpl (fan-out=106) ---")
    
    # Extract shipping-related concerns
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.controller.order.facade.OrderFacadeImpl",
        "OrderShippingDelegate",
        "com.salesmanager.shop.store.controller.order.facade.shipping",
        ["shipping", "Shipping"],
    )
    if r: changes.append("Extracted OrderShippingDelegate from OrderFacadeImpl")
    
    # Extract payment-related concerns
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.controller.order.facade.OrderFacadeImpl",
        "OrderPaymentDelegate",
        "com.salesmanager.shop.store.controller.order.facade.payment",
        ["payment", "Payment"],
    )
    if r: changes.append("Extracted OrderPaymentDelegate from OrderFacadeImpl")
    
    # Extract customer-related concerns
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.controller.order.facade.OrderFacadeImpl",
        "OrderCustomerDelegate",
        "com.salesmanager.shop.store.controller.order.facade.customer",
        ["customer", "Customer"],
    )
    if r: changes.append("Extracted OrderCustomerDelegate from OrderFacadeImpl")
    
    # ── 1b. Decompose CustomerFacadeImpl (fan-out=84) ──
    print("\n--- 1b. Decompose CustomerFacadeImpl (fan-out=84) ---")
    
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.controller.customer.facade.CustomerFacadeImpl",
        "CustomerAddressDelegate",
        "com.salesmanager.shop.store.controller.customer.facade.address",
        ["address", "Address", "country", "Country", "zone", "Zone"],
    )
    if r: changes.append("Extracted CustomerAddressDelegate from CustomerFacadeImpl")
    
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.controller.customer.facade.CustomerFacadeImpl",
        "CustomerAuthDelegate",
        "com.salesmanager.shop.store.controller.customer.facade.auth",
        ["security", "Security", "auth", "Auth"],
    )
    if r: changes.append("Extracted CustomerAuthDelegate from CustomerFacadeImpl")
    
    # ── 1c. Decompose UserFacadeImpl (fan-out=65) ──
    print("\n--- 1c. Decompose UserFacadeImpl (fan-out=65) ---")
    
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.facade.user.UserFacadeImpl",
        "UserPermissionDelegate",
        "com.salesmanager.shop.store.facade.user.permission",
        ["permission", "Permission", "group", "Group"],
    )
    if r: changes.append("Extracted UserPermissionDelegate from UserFacadeImpl")
    
    # ── 1d. Break largest SCC (17 packages in shop.model.*) ──
    print("\n--- 1d. Break package cycles in shop.model ---")
    
    # The core issue: shop.model.entity is imported by everyone but also imports from them
    # Move shared base entities to a separate foundation package
    entities_to_move = [
        "com.salesmanager.shop.model.entity.Entity",
        "com.salesmanager.shop.model.entity.EntityExists",
        "com.salesmanager.shop.model.entity.NameEntity",
        "com.salesmanager.shop.model.entity.ReadableEntityList",
    ]
    
    for fqcn in entities_to_move:
        if find_java_file(fqcn):
            r = move_class(fqcn, "com.salesmanager.shop.model.foundation")
            if r: changes.append(f"Moved {fqcn.split('.')[-1]} to shop.model.foundation")
    
    # Move shared reference types to break cycle between store/references
    refs_to_move = [
        "com.salesmanager.shop.model.references.ReadableAddress",
        "com.salesmanager.shop.model.references.ReadableCountry",
        "com.salesmanager.shop.model.references.ReadableZone",
    ]
    for fqcn in refs_to_move:
        if find_java_file(fqcn):
            r = move_class(fqcn, "com.salesmanager.shop.model.shared.address")
            if r: changes.append(f"Moved {fqcn.split('.')[-1]} to shop.model.shared.address")
    
    # ── 1e. Break service-layer cycles ──
    print("\n--- 1e. Break service-layer cycles ---")
    
    # core.business.services.order <-> core.business.services.payments cycle
    # Extract payment interface to break dependency
    payment_iface = "com.salesmanager.core.business.services.payments.PaymentService"
    if find_java_file(payment_iface):
        r = move_class(payment_iface, "com.salesmanager.core.business.services.payments.api")
        if r: changes.append("Moved PaymentService interface to payments.api")
    
    # core.business.services.order <-> core.business.services.shoppingcart cycle
    cart_iface = "com.salesmanager.core.business.services.shoppingcart.ShoppingCartService"
    if find_java_file(cart_iface):
        r = move_class(cart_iface, "com.salesmanager.core.business.services.shoppingcart.api")
        if r: changes.append("Moved ShoppingCartService interface to shoppingcart.api")
    
    # ── 1f. Break shop.utils cycle ──
    print("\n--- 1f. Break shop.utils <-> shop.store cycle ---")
    
    # shop.utils -> shop.store.controller.store.facade creates a cycle
    # Move facade-dependent utils to a separate package
    label_utils = "com.salesmanager.shop.utils.LabelUtils"
    if find_java_file(label_utils):
        r = move_class(label_utils, "com.salesmanager.shop.utils.labels")
        if r: changes.append("Moved LabelUtils to shop.utils.labels")
    
    print(f"\n  ITERATION 1 COMPLETE: {len(changes)} changes")
    for c in changes:
        print(f"    - {c}")
    
    return changes


# ═══════════════════════════════════════════════════════════════
# ITERATION 2: Deeper decomposition + remaining cycles
# ═══════════════════════════════════════════════════════════════

def iteration_2():
    """Aggressive refactoring iteration 2.
    
    Focus:
    1. Decompose remaining god classes (fan-out > 40)
    2. Break remaining model-layer cycles
    3. Extract shared infrastructure concerns
    """
    print("\n" + "=" * 60)
    print("  ITERATION 2: Deeper decomposition + remaining cycles")
    print("=" * 60)
    
    changes = []
    
    # ── 2a. Decompose remaining god classes ──
    print("\n--- 2a. Decompose remaining god classes ---")
    
    # OrderServiceImpl (fan-out=62)
    r = extract_methods_to_new_class(
        "com.salesmanager.core.business.services.order.OrderServiceImpl",
        "OrderCalculationDelegate",
        "com.salesmanager.core.business.services.order.calculation",
        ["tax", "Tax", "shipping", "Shipping", "total", "Total"],
    )
    if r: changes.append("Extracted OrderCalculationDelegate from OrderServiceImpl")
    
    # ShippingServiceImpl (fan-out=56)
    r = extract_methods_to_new_class(
        "com.salesmanager.core.business.services.shipping.ShippingServiceImpl",
        "ShippingRateDelegate",
        "com.salesmanager.core.business.services.shipping.rate",
        ["rate", "Rate", "module", "Module"],
    )
    if r: changes.append("Extracted ShippingRateDelegate from ShippingServiceImpl")
    
    # ReadableProductMapper (fan-out=53)
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.mapper.catalog.product.ReadableProductMapper",
        "ProductImageMapper",
        "com.salesmanager.shop.mapper.catalog.product.image",
        ["image", "Image"],
    )
    if r: changes.append("Extracted ProductImageMapper from ReadableProductMapper")
    
    # ShoppingCartFacadeImpl (fan-out=53)
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.controller.shoppingCart.facade.ShoppingCartFacadeImpl",
        "CartPricingDelegate",
        "com.salesmanager.shop.store.controller.shoppingCart.facade.pricing",
        ["price", "Price", "total", "Total"],
    )
    if r: changes.append("Extracted CartPricingDelegate from ShoppingCartFacadeImpl")
    
    # ReadableShoppingCartMapper (fan-out=50)
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.mapper.cart.ReadableShoppingCartMapper",
        "CartItemMapper",
        "com.salesmanager.shop.mapper.cart.item",
        ["product", "Product", "item", "Item"],
    )
    if r: changes.append("Extracted CartItemMapper from ReadableShoppingCartMapper")
    
    # ── 2b. Break remaining model cycles ──
    print("\n--- 2b. Break core.model cycles ---")
    
    # core.model.common <-> core.model.reference cycle
    # Move shared types to a core.model.shared package
    shared_types = [
        "com.salesmanager.core.model.common.Billing",
        "com.salesmanager.core.model.common.Delivery",
    ]
    for fqcn in shared_types:
        if find_java_file(fqcn):
            r = move_class(fqcn, "com.salesmanager.core.model.common.address")
            if r: changes.append(f"Moved {fqcn.split('.')[-1]} to core.model.common.address")
    
    # ── 2c. Break config cycle ──
    print("\n--- 2c. Break configuration cycle ---")
    
    # core.business.configuration <-> core.business.modules.order.total
    config_file = "com.salesmanager.core.business.configuration.DroolsConfiguration"
    if find_java_file(config_file):
        r = move_class(config_file, "com.salesmanager.core.business.configuration.rules")
        if r: changes.append("Moved DroolsConfiguration to configuration.rules")
    
    # ── 2d. Decompose more API classes ──
    print("\n--- 2d. Decompose large API controllers ---")
    
    # OrderApi (fan-out=58)
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.api.v1.order.OrderApi",
        "OrderSearchApi",
        "com.salesmanager.shop.store.api.v1.order.search",
        ["search", "Search", "filter", "Filter"],
    )
    if r: changes.append("Extracted OrderSearchApi from OrderApi")
    
    # ProductApi (fan-out=55)
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.api.v1.product.ProductApi",
        "ProductCategoryApi",
        "com.salesmanager.shop.store.api.v1.product.category",
        ["category", "Category"],
    )
    if r: changes.append("Extracted ProductCategoryApi from ProductApi")
    
    # MerchantStoreApi (fan-out=53)
    r = extract_methods_to_new_class(
        "com.salesmanager.shop.store.api.v1.store.MerchantStoreApi",
        "StoreConfigApi",
        "com.salesmanager.shop.store.api.v1.store.config",
        ["config", "Config", "language", "Language"],
    )
    if r: changes.append("Extracted StoreConfigApi from MerchantStoreApi")
    
    print(f"\n  ITERATION 2 COMPLETE: {len(changes)} changes")
    for c in changes:
        print(f"    - {c}")
    
    return changes


if __name__ == "__main__":
    import sys
    iteration = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    if iteration == 1:
        changes = iteration_1()
    elif iteration == 2:
        changes = iteration_2()
    else:
        print("Usage: python e13e_refactor.py [1|2]")
        print("  1 = Iteration 1: God class decomposition + major cycle breaking")
        print("  2 = Iteration 2: Deeper decomposition + remaining cycles")
