# EBS Volume Burstable IOPS Credits Exporter

This monitor is designed to make available to Prometheus the percentage of the volume's available IOPS Burst credits (`BurstBalance`). Once every 5 minutes the exporter will query the CloudWatch API for every [eligible EBS volume's](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-volume-status.html) credit balance. API calls are aligned on the time.

For example, with the defalt `CLOUDWATCH_PERIOD` of 5 minutes and the current time is 09:39 the exporter will request data from 09:30 to 09:35 in order to have a full section of data since 09:35 to 09:39 isn't a full period.

**Important Note:** There will be periodic gaps in data, so it is best to look at longer timeframe metrics to get a full picture of a volume's trends.

## Prometheus Output

There is a single metric exported by this called `ebs_iops_credits`, with a label (`vol_id`) to identify the volume ID.

Sample output:

        ebs_iops_credits{vol_id="vol-014af783630be124f"} 100.0
        ebs_iops_credits{vol_id="vol-044cd415ff43f4b8e"} 99.0
        ebs_iops_credits{vol_id="vol-0ebc628919302de8a"} 99.6
        ebs_iops_credits{vol_id="vol-0e1bac04100cd38bc"} 100.0
        ebs_iops_credits{vol_id="vol-028535af4afb673bc"} 99.0
        ebs_iops_credits{vol_id="vol-09c3c22680e68ebbb"} 100.0

## Required IAM Roles

This exporter requires access to

* `cloudwatch:ListMetrics`
* `cloudwatch:GetMetricData`

## Installation Process

Installation of the exporter is a multi-step process. Step one is to use the provided Makefile to render various templates into OpenShift YAML manifests.

### Rendering Templates with Make

A total of three variables must be provided with make:

* `AWS_REGION` - The region to make AWS API calls against
* `AWS_ACCESS_KEY_ID` - The AWS access key ID
* `AWS_SECRET_ACCESS_KEY` - The AWS secret access key

Optionally, a different image version can be provided with the `IMAGE_VERSION` variable. The defalt is `stable`.

Currently these are provided as environment variables to `make`.

`make all` will render these manifests:

* `deploy/025_sourcecode.yaml`
* `deploy/030_secrets.yaml`
* `deploy/040_deployment.yaml`

Once these have been created the collection of manifests can be applied in the usual fashion (such as `oc apply -f`).

### Additional Make Targets

The Makefile includes three helpful targets:

* `clean` - Delete any of the rendered manifest files which the Makefile renders
* `filelist` - Echos to the terminal a list of all the YAML files in the `deploy` directory
* `resourcelist` - Echos to the terminal a list of OpenShift/Kubernetes objects created by the manifests in the `deploy` directory, which may be useful for those wishing to delete the installation of this monitor.

### Prometheus Rules

Rules are provided by the [openshift/managed-cluster-config](https://github.com/openshift/managed-cluster-config) repository.
