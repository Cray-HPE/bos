
@Library('dst-shared@release/shasta-1.3') _

dockerBuildPipeline {
    repository = "cray"
    imagePrefix = "cray"
    app = "bos"
    name = "bos"
    description = "Cray Management System Boot Orchestration Service (BOS)"
    product = "shasta-premium,shasta-standard"
    enableSonar = true
    receiveEvent = ["BOA"]
}
