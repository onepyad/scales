 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/README.md
index 0000000..9dba975 100644
--- a//dev/null
+++ b/README.md
@@ -0,0 +1,15 @@
+# Scales Project
+
+This repository contains scripts and service files used to run the weight and laser measurement service.
+
+## Installation
+
+Install Python dependencies using `pip` and the provided `requirements.txt` file:
+
+```bash
+pip install -r requirements.txt
+```
+
+## Services
+
+Systemd service files can be found under `etc/systemd/system`. Python scripts are located in `usr/sbin/wsh`.
 
EOF
)
