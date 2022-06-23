# cray-bos Helm chart

In most cases the resources here should be left at their defaults. Should you need to add additional resources to your helm chart, you have the ability to do so. If you find that you're making changes that might be applicable to other Cray services, you're encouraged to submit a pull request to [the base service chart](https://github.com/Cray-HPE/base-charts/tree/master/kubernetes/cray-service/values.yaml).

## Description
This chart provides the Boot Orchestration Service (BOS) micro-service. It is responsible for orchestrating the power operations on components, like compute nodes. It handles powering them on and off. It tells the Boot Script Services which boot artifacts (kernel, kernel parameters, initrd, rootfs) the node should download when it boots up. It directs the Configuration Framework Service (CFS) to configure the nodes.