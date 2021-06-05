# About
This is the Boot Orchestration Service (BOS) API. It is responsible
for stateful changes to boot orchestration sessions, and launching boot
orchestration agents (BOA) which fulfill boot-related requests.

## Related Software
*Boot Orchestration Agent* (BOA) handles boot requests submitted to the BOS API.

*Image Management Service* (IMS) owns record keeping, building and staging of
images used with a boot orchestration service Boot Set.

*Artifact Repository Service* (ARS) owns organization, upload, and serving of
files, including package repositories, root filesystems, kernels, and initrds.

*Boot Script Service* (BSS) BSS holds per hardware associations for what to boot
next. Nodes consult BSS for their target artifacts and boot parameters when nodes
boot, reboot, or initially power on.

*Configuration Framework Service* (CFS) is a CRD-enabled API that launches and
aggregates status from one or more ansible instances against 
nodes (Node Personalization) or Images (Image Customization).

## Terminology
* Operation -- an operation to perform on some nodes
  * Boot -- Boot nodes that are off
  * Reboot -- Gracefully power down nodes that are on and then power them back up
  * Shutdown -- Gracefully power down nodes that are on
  * Reconfigure -- Reconfigure the nodes using the Configuration Framework Service (CFS)  (Currently, not supported.)

* Boot Set -- A collection of nodes that you want to perform an operation upon.  It contains
  * A list of nodes
  * The following applies to booting or rebooting:
    * ims_image_id: The Image Management Service (IMS) ID of the image you want to boot/reboot the nodes with;
      This ID will help BOS find all of the boot artifacts needed to boot the nodes.
    * Kernel parameters: The kernel parameters to use to boot the nodes
    * Network: The network to boot the nodes over; Choices:
      * NMN -- Node Management Network
    * rootfs_provider_passthrough: Additional kernel parameters that will be appended to the 'rootfs=\<protocol>' kernel parameter

* Session Template -- A collection of one or more Boot Sets and some associated data
  * boot_sets: One or more Boot Sets as described above
  * partition: The machine partition to operate on
  * enable_cfs: Whether to enable the Configuration Framework Service (CFS); Choices: true/false
  * cfs_url:The The repository clone url for the repository providing the configuration.
  * cfs_branch: The name of the branch containing the configuration that you want to apply to the nodes

* Session -- Performs an Operation (action) on a Session Template.  The creation of
a Session results in the creation of one or more Kubernetes BOA jobs which interact
with other Shasta subsystems to perform the requested operation.

## Launching a Boot Session
Once the bos Ansible role has been run, then you can launch a Boot Session with
```
kubectl apply -f /root/k8s/manual.yaml
```
Because a Boot Session is a Kubernetes job, and only one Kubernetes job with a
given name can exist at a time, the previous job must be deleted.  Thus, if
the Boot Session has been launched previously, then its job will first need to
be deleted and then relaunched.
```
kubectl delete -f /root/k8s/manual.yaml
kubectl apply -f /root/k8s/manual.yaml
```

If you forget to delete the job and attempt to launch the Boot Session, you
will encounter an inscrutable error like this
```
# kubectl apply -f manual.yaml
The Job "boa-dynamic" is invalid: spec.template: Invalid value: core.PodTemplateSpec{ObjectMeta:v1.ObjectMeta{Name:"", GenerateName:"", Namespace:"", SelfLink:"", UID:"", ResourceVersion:"", Generation:0, CreationTimestamp:v1.Time{Time:time.Time{wall:0x0, ext:0, loc:(*time.Location)(nil)}}, DeletionTimestamp:(*v1.Time)(nil), DeletionGracePeriodSeconds:(*int64)(nil), Labels:map[string]string{"controller-uid":"42d9903a-7343-11e9-a1a2-a4bf0138e991", "job-name":"boa-dynamic"}, Annotations:map[string]string(nil), OwnerReferences:[]v1.OwnerReference(nil), Initializers:(*v1.Initializers)(nil), Finalizers:[]string(nil), ClusterName:""}, Spec:core.PodSpec{Volumes:[]core.Volume{core.Volume{Name:"boot-session", VolumeSource:core.VolumeSource{HostPath:(*core.HostPathVolumeSource)(nil), EmptyDir:(*core.EmptyDirVolumeSource)(nil), GCEPersistentDisk:(*core.GCEPersistentDiskVolumeSource)(nil), AWSElasticBlockStore:(*core.AWSElasticBlockStoreVolumeSource)(nil), GitRepo:(*core.GitRepoVolumeSource)(nil), Secret:(*core.SecretVolumeSource)(nil), NFS:(*core.NFSVolumeSource)(nil), ISCSI:(*core.ISCSIVolumeSource)(nil), Glusterfs:(*core.GlusterfsVolumeSource)(nil), PersistentVolumeClaim:(*core.PersistentVolumeClaimVolumeSource)(nil), RBD:(*core.RBDVolumeSource)(nil), Quobyte:(*core.QuobyteVolumeSource)(nil), FlexVolume:(*core.FlexVolumeSource)(nil), Cinder:(*core.CinderVolumeSource)(nil), CephFS:(*core.CephFSVolumeSource)(nil), Flocker:(*core.FlockerVolumeSource)(nil), DownwardAPI:(*core.DownwardAPIVolumeSource)(nil), FC:(*core.FCVolumeSource)(nil), AzureFile:(*core.AzureFileVolumeSource)(nil), ConfigMap:(*core.ConfigMapVolumeSource)(0xc00b6ca280), VsphereVolume:(*core.VsphereVirtualDiskVolumeSource)(nil), AzureDisk:(*core.AzureDiskVolumeSource)(nil), PhotonPersistentDisk:(*core.PhotonPersistentDiskVolumeSource)(nil), Projected:(*core.ProjectedVolumeSource)(nil), PortworxVolume:(*core.PortworxVolumeSource)(nil), ScaleIO:(*core.ScaleIOVolumeSource)(nil), StorageOS:(*core.StorageOSVolumeSource)(nil)}}}, InitContainers:[]core.Container(nil), Containers:[]core.Container{core.Container{Name:"boa-dynamic", Image:"sms.local:5000/jasons/cray-boa:latest", Command:[]string(nil), Args:[]string(nil), WorkingDir:"", Ports:[]core.ContainerPort(nil), EnvFrom:[]core.EnvFromSource(nil), Env:[]core.EnvVar{core.EnvVar{Name:"NAMESPACE", Value:"default", ValueFrom:(*core.EnvVarSource)(nil)}, core.EnvVar{Name:"OPERATION", Value:"shutdown", ValueFrom:(*core.EnvVarSource)(nil)}}, Resources:core.ResourceRequirements{Limits:core.ResourceList(nil), Requests:core.ResourceList(nil)}, VolumeMounts:[]core.VolumeMount{core.VolumeMount{Name:"boot-session", ReadOnly:false, MountPath:"/mnt/boot_session", SubPath:"", MountPropagation:(*core.MountPropagationMode)(nil)}}, VolumeDevices:[]core.VolumeDevice(nil), LivenessProbe:(*core.Probe)(nil), ReadinessProbe:(*core.Probe)(nil), Lifecycle:(*core.Lifecycle)(nil), TerminationMessagePath:"/dev/termination-log", TerminationMessagePolicy:"File", ImagePullPolicy:"Always", SecurityContext:(*core.SecurityContext)(nil), Stdin:false, StdinOnce:false, TTY:false}}, RestartPolicy:"Never", TerminationGracePeriodSeconds:(*int64)(0xc005979df8), ActiveDeadlineSeconds:(*int64)(nil), DNSPolicy:"ClusterFirst", NodeSelector:map[string]string(nil), ServiceAccountName:"", AutomountServiceAccountToken:(*bool)(nil), NodeName:"", SecurityContext:(*core.PodSecurityContext)(0xc002407ce0), ImagePullSecrets:[]core.LocalObjectReference(nil), Hostname:"", Subdomain:"", Affinity:(*core.Affinity)(nil), SchedulerName:"default-scheduler", Tolerations:[]core.Toleration(nil), HostAliases:[]core.HostAlias(nil), PriorityClassName:"", Priority:(*int32)(nil), DNSConfig:(*core.PodDNSConfig)(nil), ReadinessGates:[]core.PodReadinessGate(nil), RuntimeClassName:(*string)(nil), EnableServiceLinks:(*bool)(nil)}}: field is immutable
```
In that case, simply delete the job first and then relaunch it.

If you want to change the operation that is run on the nodes, such as
shutting down the nodes rather than booting them, you can edit
the file /root/k8s/manual.yaml and the change the operation.

The manual.yaml file looks like this.
```
# less manual.yaml
kind: Job
apiVersion: batch/v1
metadata:
  name: boa-dynamic
spec:
  template:
    spec:
      containers:
      - name: boa-dynamic
        image: sms.local:5000/jasons/cray-boa:latest
        env:
        - name: NAMESPACE
          value: default
        - name: OPERATION
          value: shutdown    <<<< Change this value.
        volumeMounts:
        - name: boot-session
          mountPath: /mnt/boot_session
      volumes:
      - name: boot-session
        configMap:
          name: cray-boot-session
      restartPolicy: Never
  backoffLimit: 4
```

## Testing

### Unit tests

#### Run unit tests and codestyle checkers with Docker

```
$ ./run_unittests

$ ./run_codestylecheck
```

### CT Tests

See cms-tools repo for details on running CT tests for this service.

#### Run API tests with docker

```
$ docker build . -t bos-api-testing --target api-testing
$ docker run --rm \
  -e OAUTH_CLIENT_SECRET=$(kubectl get secrets admin-client-auth -ojsonpath='{.data.client-secret}' | base64 -d && echo) \
  -e TLS_VERIFY=false \
  bos-api-testing
```

## Generating the server

The OpenAPI specification automatically generates server code as a function of
building the docker image, however, it may be desirable to generate the server code
while writing and testing code locally, outside of the docker image itself. This
is helpful when the openapi code in question generates stubbed content, to be later
filled in by the application developer.

_NOTE_: Generated code that does not have Cray authored additions should not be
checked in for this repository. The .gitignore file has patterns that match
generated code to help prevent this kind of check-in.

To manually update the server code into your local checkout, run the following command:

```
$ cd $REPO
$ ./regenerate-server.sh
```

## Versioning
Use [SemVer](http://semver.org/). The version generated by the [.version](.version) script.
All other files have the version string written to them at build time based on the information
in the [update_versions.conf](update_versions.conf) file.

## Build Helpers
This repo uses some build helper scripts from the cms-meta-tools repo. See that repo for more details.

## Copyright and License
This project is copyrighted by Hewlett Packard Enterprise Development LP and is under the MIT
license. See the [LICENSE](LICENSE) file for details.

When making any modifications to a file that has a Cray/HPE copyright header, that header
must be updated to include the current year.

When creating any new files in this repo, if they contain source code, they must have
the HPE copyright and license text in their header, unless the file is covered under
someone else's copyright/license (in which case that should be in the header). For this
purpose, source code files include Dockerfiles, Ansible files, RPM spec files, and shell
scripts. It does **not** include Jenkinsfiles, OpenAPI/Swagger specs, or READMEs.

When in doubt, provided the file is not covered under someone else's copyright or license, then
it does not hurt to add ours to the header.
