SHELL := /bin/bash

# All of the source files which compose the monitor. 
# Important note: No directory structure will be maintained
SOURCEFILES ?= monitor/main.py monitor/start.sh

IMAGE_VERSION ?= stable
INIT_IMAGE_VERSION ?= 1903.0.0

RESOURCELIST := servicemonitor/ebs-iops-reporter service/ebs-iops-reporter \
	deployment/ebs-iops-reporter secret/ebs-iops-reporter-credentials-volume \
	configmap/ebs-iops-reporter-code rolebinding/sre-ebs-iops-reporter \
	serviceaccount/sre-ebs-iops-reporter clusterrole/sre-allow-read-cluster-setup \
	rolebinding/sre-ebs-iops-reporter-read-cluster-setup CredentialsRequest/ebs-iops-reporter-aws-credentials \
	secrets/ebs-iops-reporter-aws-credentials

all: deploy/025_sourcecode.yaml deploy/040_deployment.yaml

deploy/025_sourcecode.yaml: $(SOURCEFILES)
	for sfile in $(SOURCEFILES); do \
		files="--from-file=$$sfile $$files" ; \
	done ; \
	kubectl -n openshift-monitoring create configmap ebs-iops-reporter-code --dry-run=true -o yaml $$files 1> deploy/025_sourcecode.yaml

deploy/040_deployment.yaml: resources/040_deployment.yaml.tmpl
	@sed \
		-e "s/\$$IMAGE_VERSION/$(IMAGE_VERSION)/g" \
		-e "s/\$$INIT_IMAGE_VERSION/$(INIT_IMAGE_VERSION)/g" \
	resources/040_deployment.yaml.tmpl 1> deploy/040_deployment.yaml

.PHONY: clean
clean:
	rm -f deploy/025_sourcecode.yaml deploy/040_deployment.yaml

.PHONY: filelist
filelist: all
	@ls -1 deploy/*.y*ml

.PHONE: resourcelist
resourcelist:
	@echo $(RESOURCELIST)