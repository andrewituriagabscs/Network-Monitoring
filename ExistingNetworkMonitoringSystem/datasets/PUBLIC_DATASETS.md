# Public ping and reachability datasets

These public sources can support ping/reachability research, but they are not direct system inputs. This application only monitors hosts you discover and select on your local network.

| Dataset | Match | What it contains | Source |
| --- | --- | --- | --- |
| RIPE Atlas ping measurements | Direct ICMP latency and reachability match; external probe network | Public measurements from probes worldwide; not measurements of the PCs discovered by this app | https://atlas.ripe.net/ |
| CAIDA Internet Outages dataset | Reachability/outage research match; not per-PC ping history | Annotated Internet outage events suitable for research context and evaluation design | https://www.caida.org/catalog/datasets/ |
| MAWI Working Group traces | ICMP traffic context; not ping RTT series | Real backbone packet traces; selected traces include substantial ICMP traffic | https://mawi.wide.ad.jp/mawi/ |

## Recommended thesis use

Use RIPE Atlas when external ICMP latency/reachability measurements are needed. Use the live SQLite export in this project for measurements from selected local PCs:

```powershell
python export_dataset.py
```

The local feature schema is in `ping_dataset.csv`. It includes target, ICMP reachability, latency, packet loss, and `anomaly_label`.

External probe records should not be described as measurements from locally monitored PCs. Keep their source and probe metadata with any downloaded dataset and follow its terms of use.