# Be sure to add new variables to this function
define generate_file
	sed \
		-e "s!\$$EXPORTER_NAME!$(EXPORTER_NAME)!g" \
		-e "s!\$$PREFIXED_NAME!$(PREFIXED_NAME)!g" \
		-e "s!\$$MAIN_IMAGE!$(MAIN_IMAGE)!g" \
		-e "s!\$$INIT_IMAGE!$(INIT_IMAGE)!g" \
		-e "s!\$$SERVICEACCOUNT_NAME!$(SERVICEACCOUNT_NAME)!g" \
		-e "s!\$$SOURCE_CONFIGMAP_NAME!$(SOURCE_CONFIGMAP_NAME)!g" \
		-e "s!\$$AWS_CREDENTIALS_SECRET_NAME!$(AWS_CREDENTIALS_SECRET_NAME)!g" \
	resources/$(1).yaml.tmpl 1> deploy/$(1).yaml
endef