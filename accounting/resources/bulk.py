from import_export import resources

class BulkCreateResource(resources.ModelResource):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instances_to_create = []

    def save_instance(self, *args, **kwargs):
        dry_run = kwargs.get('dry_run', False)
        if not dry_run:
            instance = kwargs.get('instance')
            if len(args) >= 1:
                instance = args[0]
            self.instances_to_create.append(instance)

    def after_import(self, dataset, result, *args, **kwargs):
        dry_run = kwargs.get('dry_run', False)
        if not dry_run and self.instances_to_create:
            self.Meta.model.objects.bulk_create(self.instances_to_create, batch_size=1000)
            self.instances_to_create.clear()
