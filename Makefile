SHELL := /bin/bash

# All of the source files which compose the monitor. 
# Important note: No directory structure will be maintained
SOURCEFILES ?= monitor/main.py

IMAGE_VERSION ?= stable
RESOURCELIST := servicemonitor/ebs-iops-reporter service/ebs-iops-reporter deployment/ebs-iops-reporter secret/ebs-iops-reporter-credentials-volume configmap/ebs-iops-reporter-code rolebinding/sre-ebs-iops-reporter serviceaccount/sre-ebs-iops-reporter

all: deploy/025_sourcecode.yaml deploy/030_secrets.yaml deploy/040_deployment.yaml

.PHONY: check-env
check-env:
ifndef AWS_REGION
	$(error Please set AWS_REGION)
endif
ifndef AWS_SECRET_ACCESS_KEY
	$(error Please set AWS_SECRET_ACCESS_KEY)
endif
ifndef AWS_ACCESS_KEY_ID
	$(error Please set AWS_ACCESS_KEY_ID)
endif

deploy/025_sourcecode.yaml: $(SOURCEFILES)
	@echo "Creating $(@)" ; \
	for sfile in $(SOURCEFILES); do \
		files="--from-file=$$sfile $$files" ; \
	done ; \
	kubectl -n openshift-monitoring create configmap ebs-iops-reporter-code --dry-run=true -o yaml $$files 1> deploy/025_sourcecode.yaml

deploy/040_deployment.yaml: check-env
	@echo "Creating $(@)" ; \
	sed \
		-e "s/\$$IMAGE_VERSION/$(IMAGE_VERSION)/g" \
	resources/040_deployment.yaml.tmpl 1> deploy/040_deployment.yaml

deploy/030_secrets.yaml: check-env
	@echo "Creating $(@)" ; \
	umask 077 ; \
	tmpdir=$(shell mktemp -d $(self)) ; \
	if [[ ! -d $$tmpdir ]]; then \
		echo "Not able to create temp dir for secrets. Giving up" ;\
		exit 1 ;\
	fi ;\
	echo "  Temporary dir=$$tmpdir" ; \
	sed \
		-e "s/\$$AWS_ACCESS_KEY_ID/$$AWS_ACCESS_KEY_ID/g" \
		-e "s/\$$AWS_SECRET_ACCESS_KEY/$$AWS_SECRET_ACCESS_KEY/g" \
	resources/secrets-credentials.tmpl 1> $$tmpdir/credentials ; \
	sed \
		-e "s/\$$AWS_REGION/$$AWS_REGION/g" \
	resources/secrets-config.tmpl 1> $$tmpdir/config ; \
	kubectl \
		-n openshift-monitoring \
		create secret generic ebs-iops-reporter-credentials-volume \
		--dry-run=true -o yaml \
		--from-file=$$tmpdir/credentials --from-file=$$tmpdir/config \
		1> deploy/030_secrets.yaml ; \
	echo "  Cleaning temp dir ($$tmpdir)" ; \
	rm -rf $$tmpdir

.PHONY: clean
clean:
	rm -f deploy/025_sourcecode.yaml deploy/030_secrets.yaml deploy/040_deployment.yaml

.PHONY: filelist
filelist: all
	@ls -1 deploy/*.y*ml

.PHONE: resourcelist
resourcelist:
	@echo $(RESOURCELIST)