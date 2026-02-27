#!/usr/bin/env python3
"""
generate-module-poms.py

Lee el Bundle-SymbolicName real de cada MANIFEST.MF y genera el pom.xml
correcto para ese modulo.

Tycho 4.x exige que artifactId == Bundle-SymbolicName exactamente.
Si no coinciden falla con:
  "The Maven artifactId must be the same as the bundle symbolic name"

Este script corre antes del mvn package en el workflow de GitHub Actions.
"""
import os
import re

PARENT_GROUP    = "au.com.langdale.cimtool"
PARENT_ARTIFACT = "cimtool-parent"
PARENT_VERSION  = "2.2.0-SNAPSHOT"

PLUGIN_POM = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>{parent_group}</groupId>
    <artifactId>{parent_artifact}</artifactId>
    <version>{parent_version}</version>
    <relativePath>../pom.xml</relativePath>
  </parent>
  <!-- artifactId DEBE ser identico al Bundle-SymbolicName del MANIFEST.MF -->
  <artifactId>{artifact_id}</artifactId>
  <packaging>eclipse-plugin</packaging>
</project>
"""

FEATURE_POM = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>{parent_group}</groupId>
    <artifactId>{parent_artifact}</artifactId>
    <version>{parent_version}</version>
    <relativePath>../pom.xml</relativePath>
  </parent>
  <artifactId>{artifact_id}</artifactId>
  <packaging>eclipse-feature</packaging>
</project>
"""

def get_bsn(manifest_path):
    """Extrae Bundle-SymbolicName de un MANIFEST.MF (ignora atributos como ;singleton:=true)"""
    try:
        content = open(manifest_path, encoding='utf-8', errors='replace').read()
        m = re.search(r'^Bundle-SymbolicName:\s*([^\s;]+)', content, re.MULTILINE)
        return m.group(1).strip() if m else None
    except Exception as e:
        print(f"  ERROR leyendo {manifest_path}: {e}")
        return None

def get_feature_id(feature_path):
    """Extrae el id de una feature.xml"""
    try:
        content = open(feature_path, encoding='utf-8', errors='replace').read()
        m = re.search(r'<feature[^>]+\bid=["\']([^"\']+)["\']', content)
        return m.group(1) if m else None
    except Exception as e:
        print(f"  ERROR leyendo {feature_path}: {e}")
        return None

def write_pom(path, content):
    open(path, 'w', encoding='utf-8').write(content)

# Directorios a ignorar siempre
IGNORE_DIRS = {'.git', '.github', 'docs', 'target', 'node_modules'}

modules_included = []
modules_skipped  = []

print("=== Generando pom.xml de modulos ===\n")

for d in sorted(os.listdir('.')):
    if not os.path.isdir(d) or d in IGNORE_DIRS or d.startswith('.'):
        continue

    manifest_path = os.path.join(d, 'META-INF', 'MANIFEST.MF')
    feature_path  = os.path.join(d, 'feature.xml')
    pom_path      = os.path.join(d, 'pom.xml')

    # ── Eclipse Plugin (bundle OSGi) ──────────────────────────────────────────
    if os.path.exists(manifest_path):
        bsn = get_bsn(manifest_path)
        if bsn:
            write_pom(pom_path, PLUGIN_POM.format(
                parent_group=PARENT_GROUP,
                parent_artifact=PARENT_ARTIFACT,
                parent_version=PARENT_VERSION,
                artifact_id=bsn
            ))
            modules_included.append(d)
            print(f"  [eclipse-plugin]  {d:<30}  BSN={bsn}")
        else:
            modules_skipped.append(d)
            print(f"  [skip]            {d:<30}  (MANIFEST sin Bundle-SymbolicName)")

    # ── Eclipse Feature ───────────────────────────────────────────────────────
    elif os.path.exists(feature_path):
        fid = get_feature_id(feature_path)
        if fid:
            write_pom(pom_path, FEATURE_POM.format(
                parent_group=PARENT_GROUP,
                parent_artifact=PARENT_ARTIFACT,
                parent_version=PARENT_VERSION,
                artifact_id=fid
            ))
            modules_included.append(d)
            print(f"  [eclipse-feature] {d:<30}  id={fid}")
        else:
            modules_skipped.append(d)
            print(f"  [skip]            {d:<30}  (feature.xml sin id)")

    # ── CIMToolProduct (eclipse-repository, pom.xml ya existe) ───────────────
    elif os.path.exists(pom_path):
        # No tocamos los pom.xml que ya existen (CIMToolProduct tiene packaging especial)
        print(f"  [keep pom]        {d:<30}  (pom.xml existente, sin MANIFEST/feature.xml)")

    else:
        modules_skipped.append(d)
        print(f"  [no pom/manifest] {d}")

print(f"\nTotal incluidos: {len(modules_included)}")
print(f"Total omitidos:  {len(modules_skipped)}")
print(f"Modulos: {modules_included}")