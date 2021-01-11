
@Library('dst-shared@master') _

dockerBuildPipeline {
    repository = "cray"
    imagePrefix = "cray"
    app = "bos"
    name = "bos"
    description = "Cray Management System Boot Orchestration Service (BOS)"
    product = "csm"
    enableSonar = true
    receiveEvent = ["BOA"]
}
