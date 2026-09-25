# Public datasets for comparison

These sources are suitable for comparison with this system, but they do not all contain the same measurements. The distinction matters for a thesis.

| Dataset | Match | What it contains | Source |
| --- | --- | --- | --- |
| CIC-IDS2017 | Strong anomaly-label match; not SNMP-MIB | Labeled benign and attack network flows, including DoS, DDoS, scans, brute force, and web attacks | https://www.unb.ca/cic/datasets/ids-2017.html |
| CSE-CIC-IDS2018 | Strong anomaly-label match; not SNMP-MIB | Labeled network-flow CSV files with protocol, packet, byte, duration, and attack-label features | https://registry.opendata.aws/cse-cic-ids2018/ |
| MAWI Working Group traces / MAWILab labels | Strong traffic and anomaly match; not SNMP-MIB | Real backbone packet traces, anomaly labels, and substantial ICMP traffic in selected traces | https://mawi.wide.ad.jp/mawi/ |
| SNMP-MIB anomaly paper dataset | Exact conceptual match; download not confirmed | SNMP-MIB telemetry used for anomaly detection in Al-Naymat et al. (2021) | https://doi.org/10.1504/IJCAT.2021.119606 |

## Recommended thesis use

Use CIC-IDS2017 or CSE-CIC-IDS2018 for labeled anomaly-model benchmarking. Use MAWI/MAWILab for traffic and anomaly context. Use the live SQLite export in this project for the SNMP-MIB plus active-ICMP experiment:

```powershell
python export_dataset.py
```

The local feature schema is in `snmp_mib_dataset.csv`. It includes `mib_in_octets`, `mib_out_octets`, `mib_in_errors`, `mib_out_errors`, their derived rates, ICMP reachability/latency, and `anomaly_label`.

Do not describe CIC or MAWI rows as SNMP-MIB measurements. They should be reported as external comparison datasets, while the project export is the SNMP-MIB/ICMP dataset collected by the proposed system.