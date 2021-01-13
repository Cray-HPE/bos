
@Library('dst-shared@release/shasta-1.4') _

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
