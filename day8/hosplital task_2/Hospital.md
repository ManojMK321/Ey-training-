&#x09;				**Azure-Based Architecture for Patient Portals, Clinical APIs, and Medical Imaging**



|Requirement|Classification|Key Deciding Factor|
|-|-|-|
|Patient web portal|Application Gateway|Needs URL-path routing (/api/\\\*, /static/\\\*), SSL termination, and WAF for OWASP Top 10 — all Layer 7 HTTP features|
|Clinical API (internal)|Load Balancer|Pure internal VNet TCP traffic on port 8443, no HTTP inspection needed, sub-millisecond latency required — classic Layer 4 use case|
|Auth service (header routing)|Application Gateway|Must inspect the `X-Trust-ID` HTTP header to route to the correct trust pool — requires Layer 7 header awareness; end-to-end TLS also fits App Gateway|
| Legacy SOAP lab service|Load Balancer|Internal-only TCP port 9090, vendor forbids payload/header modification, only needs simple failover redundancy — minimal Layer 4 config|
|Admin dashboard (hostname)|Application Gateway|Two hostnames on one public IP routed to different backend pools, plus autoscaling and HTTPS — hostname-based routing is a Layer 7 / App Gateway feature|

**Quick rule of thumb from your slide**: 

&#x09;if it's HTTP/HTTPS with routing logic or WAF → Application Gateway; 

&#x09;if it's raw TCP/UDP, internal, or needs ultra-low latency with no inspection → Load Balancer







Here's the breakdown for each section:



**① Patient web portal** → Application Gateway

Traffic arrives from the public internet over HTTPS. App Gateway terminates SSL at the edge, fires the WAF to block SQL injection and XSS, then inspects the URL path: /api/\* routes to the REST API backend pool, /static/\* routes to Azure Blob Storage. This is pure Layer 7 work — a Load Balancer has no concept of URL paths.



② **Clinical API (internal)** → Load Balancer

Hospital EHR systems inside the VNet send HL7 FHIR messages over raw TCP port 8443. There's no HTTP, no headers to inspect, no WAF needed. A Load Balancer distributes connections across the 12-VM pool in sub-millisecond time and costs far less than App Gateway for this simple job.



③ **DICOM image streaming** → Load Balancer

Radiologists push 50–200 MB raw TCP streams from workstations to image-processing VMs. The connection must stay pinned to one VM for the entire transfer (session persistence via source IP affinity on the Load Balancer). There's no HTTP framing, so App Gateway would break or be irrelevant here.



④ **Auth service (header routing)** → Application Gateway

Every login request carries an X-Trust-ID HTTP header identifying the NHS trust. App Gateway reads that header and routes to the matching trust-specific backend pool (e.g. NW01 → North West pool). It also re-encrypts traffic end-to-end (TLS passthrough/re-encrypt). Header inspection is a Layer 7 capability — only App Gateway can do this.



⑤ **Legacy SOAP lab service** → Load Balancer

The SOAP/XML service runs on two VMs, called over TCP port 9090 from internal pathology systems. The vendor contract forbids touching the payload or headers. All that's needed is: if VM 1 dies, send traffic to VM 2. A Load Balancer does exactly that with minimal config and zero inspection — App Gateway would be overkill and could corrupt the untouched payload.



⑥ **Admin dashboard (hostname routing)** → Application Gateway

Both admin.healthbridge.nhs.uk and www.healthbridge.nhs.uk share a single public IP. App Gateway splits them by hostname: admin subdomain → 2-VM admin pool (with CPU-based autoscale rules), www subdomain → 6-VM public pool. Both are HTTPS. Hostname-based routing on one IP is a Layer 7 feature exclusive to App Gateway.









**Key Reasoning Highlights**

Application Gateway (Layer 7) cases

Used when intelligent HTTP(S) routing or security features are needed:





Patient portal



Needs WAF (OWASP protection)

Requires URL path routing (/api vs /static)

SSL termination required at entry point





Auth service



Requires header-based routing (tenant-specific)

Multi-tenant routing logic → Layer 7 awareness

Needs end-to-end TLS





Admin dashboard



Requires hostname-based routing (admin vs www)

Multiple apps on single public IP

HTTPS + autoscaling support







**All these involve HTTP intelligence beyond simple forwarding**



Load Balancer (Layer 4) cases

Used when raw traffic distribution without inspection is sufficient:





Clinical API



Pure TCP (port 8443)

Internal VNet only

No need for WAF, routing, or inspection





DICOM streaming



Large non-HTTP TCP payloads

Long-lived connections

Requires session persistence without processing





Legacy SOAP service



Uses raw TCP (port 9000)

Vendor prohibits payload modification

Only needs failover (redundancy)







