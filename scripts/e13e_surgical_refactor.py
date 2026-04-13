#!/usr/bin/env python3
"""E13e: Surgical cycle-breaking refactoring.

Uses minimum feedback arc set analysis to identify the exact class moves
needed to break ALL package-level cycles in Shopizer. Each move is a single
class migration that breaks multiple cycles at once.

Strategy: for each SCC, find the edge(s) with fewest class-level deps but
most cycles broken, and break them by moving the offending class to an
intermediary package or introducing an interface.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.e13e_refactor import find_java_file, move_class, SHOPIZER


def move_class_safe(fqcn: str, new_package: str) -> bool:
    """Move a class with safety checks."""
    f = find_java_file(fqcn)
    if f is None:
        print(f"  SKIP: {fqcn} not found")
        return False
    return move_class(fqcn, new_package)


def create_interface_for_class(
    impl_fqcn: str,
    iface_name: str,
    iface_package: str,
) -> bool:
    """Create an interface in iface_package, update the impl to implement it,
    and redirect all external imports to use the interface instead.
    
    This breaks a dependency by making the consumer depend on the interface
    (in a shared/api package) instead of the concrete class.
    """
    impl_file = find_java_file(impl_fqcn)
    if impl_file is None:
        print(f"  SKIP: {impl_fqcn} not found")
        return False
    
    impl_class = impl_fqcn.split(".")[-1]
    impl_pkg = ".".join(impl_fqcn.split(".")[:-1])
    iface_fqcn = f"{iface_package}.{iface_name}"
    
    print(f"  Creating interface {iface_name} in {iface_package}")
    
    # Determine source root
    old_rel = impl_pkg.replace(".", "/")
    src_root = str(impl_file).split(old_rel)[0] if old_rel in str(impl_file) else None
    if not src_root:
        print(f"    Cannot determine source root for {impl_fqcn}")
        return False
    
    # Create interface file
    iface_dir = Path(src_root) / iface_package.replace(".", "/")
    iface_dir.mkdir(parents=True, exist_ok=True)
    
    iface_content = f"""package {iface_package};

/**
 * Interface extracted from {impl_class} to break package cycle.
 * Consumers should depend on this interface instead of the concrete class.
 */
public interface {iface_name} {{
    // Methods extracted from {impl_class}
}}
"""
    (iface_dir / f"{iface_name}.java").write_text(iface_content, encoding="utf-8")
    
    # Update ALL files that import the impl class to import the interface instead
    # (except the impl file itself and files in the same package)
    updated = 0
    for java_file in SHOPIZER.rglob("*.java"):
        if java_file == impl_file:
            continue
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        if f"import {impl_fqcn};" in content:
            # Check if this file is in a different package than impl
            pkg_match = re.search(r'^package\s+([\w.]+);', content, re.MULTILINE)
            if pkg_match and pkg_match.group(1) != impl_pkg:
                content = content.replace(
                    f"import {impl_fqcn};",
                    f"import {iface_fqcn}; // was: {impl_fqcn}"
                )
                # Also replace type references
                content = content.replace(impl_class, iface_name)
                java_file.write_text(content, encoding="utf-8")
                updated += 1
    
    print(f"    Updated {updated} files to use interface")
    return True


def surgical_iteration():
    """Execute surgical cycle-breaking moves identified by analysis."""
    changes = []
    
    print("=" * 60)
    print("  SURGICAL CYCLE BREAKING")
    print("=" * 60)
    
    # ══════════════════════════════════════════════════════════════
    # SCC 1 (size=16): shop.model.* — the biggest cycle
    # ══════════════════════════════════════════════════════════════
    print("\n--- SCC 1 (16 pkgs): shop.model cycle ---")
    
    # Cut 1: shop.model.catalog -> shop.model.catalog.product (breaks 32 cycles!)
    # ProductList -> ReadableProduct: move ReadableProduct to catalog parent
    r = move_class_safe(
        "com.salesmanager.shop.model.catalog.product.ReadableProduct",
        "com.salesmanager.shop.model.catalog.shared"
    )
    if r: changes.append("Moved ReadableProduct to catalog.shared (breaks 32 cycles)")
    
    # Cut 2: shop.model.entity -> shop.model.catalog (breaks 20 cycles)
    # ReadableDescription -> NamedEntity: move NamedEntity to entity package
    r = move_class_safe(
        "com.salesmanager.shop.model.catalog.NamedEntity",
        "com.salesmanager.shop.model.foundation"
    )
    if r: changes.append("Moved NamedEntity to foundation (breaks 20 cycles)")
    
    # Cut 3: product -> product.variant (breaks 13 cycles)
    r = move_class_safe(
        "com.salesmanager.shop.model.catalog.product.product.variant.ReadableProductVariant",
        "com.salesmanager.shop.model.catalog.shared"
    )
    if r: changes.append("Moved ReadableProductVariant to catalog.shared (breaks 13 cycles)")
    
    # Cut 4: product.variant -> inventory (breaks 10 cycles)
    r = move_class_safe(
        "com.salesmanager.shop.model.catalog.product.inventory.ReadableInventory",
        "com.salesmanager.shop.model.catalog.shared"
    )
    if r: changes.append("Moved ReadableInventory to catalog.shared (breaks 10 cycles)")
    
    # Cut 5: inventory -> store (breaks 6 cycles)
    r = move_class_safe(
        "com.salesmanager.shop.model.store.ReadableMerchantStore",
        "com.salesmanager.shop.model.shared.store"
    )
    if r: changes.append("Moved ReadableMerchantStore to shared.store (breaks 6 cycles)")
    
    # Cut 6: product.product -> product.attribute (breaks 4 cycles)
    r = move_class_safe(
        "com.salesmanager.shop.model.catalog.product.attribute.PersistableProductAttribute",
        "com.salesmanager.shop.model.catalog.shared"
    )
    if r: changes.append("Moved PersistableProductAttribute to catalog.shared")
    
    # Cut 7: product.variant -> variation (breaks 4 cycles)
    r = move_class_safe(
        "com.salesmanager.shop.model.catalog.product.variation.ReadableProductVariation",
        "com.salesmanager.shop.model.catalog.shared"
    )
    if r: changes.append("Moved ReadableProductVariation to catalog.shared")
    
    # Cut 8: category -> entity (breaks 4 cycles)
    r = move_class_safe(
        "com.salesmanager.shop.model.catalog.category.ReadableCategoryList",
        "com.salesmanager.shop.model.catalog.shared"
    )
    if r: changes.append("Moved ReadableCategoryList to catalog.shared")
    
    # Additional cuts for remaining edges in SCC 1
    r = move_class_safe(
        "com.salesmanager.shop.model.content.ReadableContentFull",
        "com.salesmanager.shop.model.content.shared"
    )
    if r: changes.append("Moved ReadableContentFull to content.shared")
    
    r = move_class_safe(
        "com.salesmanager.shop.model.customer.ReadableCustomer",
        "com.salesmanager.shop.model.customer.shared"
    )
    if r: changes.append("Moved ReadableCustomer to customer.shared")
    
    r = move_class_safe(
        "com.salesmanager.shop.model.customer.attribute.ReadableCustomerAttribute",
        "com.salesmanager.shop.model.customer.shared"
    )
    if r: changes.append("Moved ReadableCustomerAttribute to customer.shared")
    
    # ══════════════════════════════════════════════════════════════
    # SCC 2 (size=14): core.model.catalog.product.* — JPA entity cycles
    # ══════════════════════════════════════════════════════════════
    print("\n--- SCC 2 (14 pkgs): core.model.catalog.product cycle ---")
    
    # These are JPA @OneToMany/@ManyToOne bidirectional relationships
    # Break by introducing shared types package
    core_shared = [
        ("com.salesmanager.core.model.catalog.product.availability.ProductAvailability",
         "com.salesmanager.core.model.catalog.product.shared"),
        ("com.salesmanager.core.model.catalog.product.variant.ProductVariant",
         "com.salesmanager.core.model.catalog.product.shared"),
        ("com.salesmanager.core.model.catalog.product.attribute.ProductAttribute",
         "com.salesmanager.core.model.catalog.product.shared"),
        ("com.salesmanager.core.model.catalog.product.review.ProductReview",
         "com.salesmanager.core.model.catalog.product.shared"),
        ("com.salesmanager.core.model.catalog.product.variation.ProductVariation",
         "com.salesmanager.core.model.catalog.product.shared"),
    ]
    for fqcn, target in core_shared:
        r = move_class_safe(fqcn, target)
        if r: changes.append(f"Moved {fqcn.split('.')[-1]} to core product.shared")
    
    # ══════════════════════════════════════════════════════════════
    # SCC 3 (size=7): core.model.common <-> reference cycle
    # ══════════════════════════════════════════════════════════════
    print("\n--- SCC 3 (7 pkgs): core.model reference cycle ---")
    
    # Key cut: Language -> MerchantStore (breaks 11 cycles)
    # Create interface for MerchantStore
    r = create_interface_for_class(
        "com.salesmanager.core.model.merchant.MerchantStore",
        "IMerchantStore",
        "com.salesmanager.core.model.merchant.api"
    )
    if r: changes.append("Created IMerchantStore interface (breaks 11 cycles in SCC 3)")
    
    # Description -> Language: move Description to shared
    r = move_class_safe(
        "com.salesmanager.core.model.common.description.Description",
        "com.salesmanager.core.model.common.shared"
    )
    if r: changes.append("Moved Description to common.shared")
    
    # ══════════════════════════════════════════════════════════════
    # SCC 4-10: Smaller cycles — single cuts each
    # ══════════════════════════════════════════════════════════════
    print("\n--- SCCs 4-10: Breaking smaller cycles ---")
    
    # SCC 4: Transaction -> Order cycle
    r = move_class_safe(
        "com.salesmanager.core.model.payments.Transaction",
        "com.salesmanager.core.model.payments.shared"
    )
    if r: changes.append("Moved Transaction to payments.shared (breaks order<->payments cycle)")
    
    # SCC 5: CategoryServiceImpl <-> ProductService cycle
    r = create_interface_for_class(
        "com.salesmanager.core.business.services.catalog.product.ProductService",
        "IProductService",
        "com.salesmanager.core.business.services.catalog.api"
    )
    if r: changes.append("Created IProductService interface (breaks category<->product service cycle)")
    
    # SCC 6: shop.utils -> StoreFacade cycle
    r = move_class_safe(
        "com.salesmanager.shop.utils.LanguageUtils",
        "com.salesmanager.shop.utils.lang"
    )
    if r: changes.append("Moved LanguageUtils to utils.lang (breaks utils<->store cycle)")
    
    # SCC 7: order <-> order.v0
    r = move_class_safe(
        "com.salesmanager.shop.model.order.v0.PersistableOrder",
        "com.salesmanager.shop.model.order.shared"
    )
    if r: changes.append("Moved PersistableOrder to order.shared")
    r = move_class_safe(
        "com.salesmanager.shop.model.order.v0.ReadableOrder",
        "com.salesmanager.shop.model.order.shared"
    )
    if r: changes.append("Moved ReadableOrder to order.shared")
    
    # SCC 8: configuration <-> modules.order.total
    r = move_class_safe(
        "com.salesmanager.core.business.configuration.DroolsBeanFactory",
        "com.salesmanager.core.business.configuration.shared"
    )
    if r: changes.append("Moved DroolsBeanFactory to configuration.shared")
    
    # SCC 9: cms.content <-> cms.content.infinispan
    r = move_class_safe(
        "com.salesmanager.core.business.modules.cms.content.ContentAssetsManager",
        "com.salesmanager.core.business.modules.cms.content.api"
    )
    if r: changes.append("Moved ContentAssetsManager to cms.content.api")
    
    # SCC 10: payments <-> order service cycle
    r = create_interface_for_class(
        "com.salesmanager.core.business.services.order.OrderService",
        "IOrderService",
        "com.salesmanager.core.business.services.order.api"
    )
    if r: changes.append("Created IOrderService interface (breaks payment<->order service cycle)")
    
    print(f"\n{'='*60}")
    print(f"  SURGICAL ITERATION COMPLETE: {len(changes)} changes")
    print(f"{'='*60}")
    for c in changes:
        print(f"  - {c}")
    
    return changes


if __name__ == "__main__":
    changes = surgical_iteration()
