# Solutions catalog naming

The former services.Service model is now services.Solution, with the admin section named Solutions. The app package/label remains services to preserve migration history. Its previous records and IDs are preserved by RenameModel, and quotation items now link through QuotationItem.solution. New uploads go under solutions/icons and solutions/images; existing services/... media paths are preserved without moving or deleting files.

The former homepage fallback model was renamed to homepage.HomepageSolution in migration 0006, then retired in migration 0007. The latter transfers unique titles to services.Solution and fills blank catalog descriptions before dropping the fallback table. Matching ignores case, whitespace and ampersand versus "and". Existing catalog IDs, descriptions, images and active flags take precedence. Old text icon names and custom button fields are retired; v2 controls those through its solution presentation and navigation.

The canonical catalog endpoint is /api/solutions/. The old /api/services/ endpoint remains a compatibility alias returning the same records. The obsolete /api/homepage-solutions/ route is removed. The homepage response also serializes the active services.Solution records with the same fields and absolute media URLs as the catalog. Both v2 pages share SolutionCatalog to read their published descriptions and images.

New quotation clients should use solution_id. The legacy service_id request key is accepted as an alias, but it cannot be combined with solution_id. Custom description items remain supported.

Deploy the backend migrations before the updated frontend, because /api/solutions/ previously returned the homepage fallback records. Run python manage.py migrate on the deployed database. The local rename was tested with existing catalog images and quotation links; a recovery snapshot is retained outside the backend repository at output/backups/before-solution-rename.sqlite3 in the workspace.
