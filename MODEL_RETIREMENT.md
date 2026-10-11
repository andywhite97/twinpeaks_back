# V2 model retirement

The following 12 application models and their public endpoints/admin screens have been retired: HeroSlide, Statistic, Brand, Testimonial, Leader, GalleryItem, Product, ProductImage, ProductCategory, Order, OrderItem, and Payment. Product feeds, checkout, payment reconciliation, purchase tracking, and quotation-to-order conversion have also been removed.

Retained models: CompanyProfile, services.Solution (formerly Service), HomepageSettings, Project, ProjectImage, ContactMessage, Quotation, QuotationItem, QuotationSequence, and User. The separate HomepageSolution fallback was subsequently merged into services.Solution and removed; both v2 pages now use the main catalog. See SOLUTION_RENAME.md for the naming and merge migrations.

The homepage API now returns only hero, settings, solutions, and projects. The sitemap lists v2 routes and published projects. Quotation requests support solution_id (with service_id as a compatibility alias) or a custom description; product_id requests are rejected. Existing quotations keep their tokens, item snapshots, prices, totals, and status history. Before removing product/order links, the migration fills missing item descriptions from the linked product and copies any converted order reference into internal notes. The converted_to_order status remains available for historical records.

The gallery, leadership, products, and orders apps must remain in INSTALLED_APPS so historical and deletion migrations can run on both existing and new databases. They have no runtime models or registered admin screens. Do not delete old migrations.

## Deployment and recovery

Take a database backup before deploying these migrations to production, then run python manage.py migrate. The build.sh deployment script already runs that command. Existing product feeds and checkout URLs will return 404 after deployment; stop any external feed refresh or payment reconciliation schedules that still target them.

Deletion migrations remove their tables and records. Reversing them recreates schemas, not the deleted records. Recover retired data from a database backup. The local pre-migration recovery snapshot is stored outside the backend Git repository at output/backups/before-v2-model-retirement.sqlite3 in the workspace. Uploaded media files have not been deleted.

Validation covers retired endpoints, current homepage and sitemap responses, service image uploads, quotation creation/view/accept/PDF/privacy, and migration of existing quotation data across the model retirement.
