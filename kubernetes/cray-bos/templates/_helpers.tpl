{{- define "cray-bos.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "cray-service.fullname" . }}
  labels:
    app.kubernetes.io/name: {{ include "cray-service.name" . }}
    {{- include "cray-service.common-labels" . | nindent 4 }}
  annotations:
    {{- include "cray-service.common-annotations" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
{{- if .Values.strategy }}
  strategy:
    {{ toYaml .Values.strategy | nindent 4 }}
    {{- if eq (.Values.strategy.type | lower) "recreate" }}
    # Need an explicit rollingUpdate: null to upgrade from default RollingUpdate
    # strategy or K8S API Server will reject the merged deployment
    rollingUpdate: null
    {{- end }}
{{- end }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "cray-service.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ include "cray-service.name" . }}
        app.kubernetes.io/instance: {{ .Release.Name }}
      annotations:
        {{- include "cray-service.pod-annotations" . | nindent 8 }}
    spec:
      {{- include "cray-service.common-spec" . | nindent 6 }}
{{- end -}}
