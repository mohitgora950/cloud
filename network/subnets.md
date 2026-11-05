# Subnet Allocation and Stateless Network Access Control (NACL)

## 1. Subnet Allocation Table

The base address block is `10.20.0.0/16`. Subnets are allocated from the largest host requirement to the smallest, using the smallest prefix length (tightest power of 2) that satisfies the host requirements. Each subnet begins immediately after the preceding subnet.

| Subnet Name | Hosts Needed | Network Address | Prefix Length | Usable Host Range | Broadcast Address | Number of Usable Hosts |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **app** | 1,000 | `10.20.0.0` | `/22` | `10.20.0.1` – `10.20.3.254` | `10.20.3.255` | 1,022 |
| **public** | 250 | `10.20.4.0` | `/24` | `10.20.4.1` – `10.20.4.254` | `10.20.4.255` | 254 |
| **data** | 100 | `10.20.5.0` | `/25` | `10.20.5.1` – `10.20.5.126` | `10.20.5.127` | 126 |
| **management** | 20 | `10.20.5.128` | `/27` | `10.20.5.129` – `10.20.5.158` | `10.20.5.159` | 30 |

---

## 2. Allocation Working and Derivations

Formula for usable hosts with prefix length $p$:
$$\text{Usable Hosts} = 2^{32 - p} - 2$$
The two reserved addresses in each IPv4 subnet are the **Network Address** (all host bits 0) and the **Broadcast Address** (all host bits 1).

### Subnet 1: `app` (Requirement: 1,000 hosts)
- Minimum addresses needed: $1000 + 2 = 1002$.
- Smallest power of 2: $2^{10} = 1024 \ge 1002$.
- Host bits: $h = 10$.
- Prefix length: $p = 32 - 10 = 22$ (`/22`).
- Usable hosts: $2^{10} - 2 = 1024 - 2 = 1022$.
- Netmask: `255.255.252.0`.
- Starting address: `10.20.0.0`.
- Network address: `10.20.0.0/22`.
- Address span: `10.20.0.0` to `10.20.3.255` (4 consecutive `/24` blocks: 10.20.0.x, 10.20.1.x, 10.20.2.x, 10.20.3.x).
- Usable host range: `10.20.0.1` through `10.20.3.254`.
- Broadcast address: `10.20.3.255`.
- Next available block starts at: `10.20.4.0`.

### Subnet 2: `public` (Requirement: 250 hosts)
- Minimum addresses needed: $250 + 2 = 252$.
- Smallest power of 2: $2^8 = 256 \ge 252$.
- Host bits: $h = 8$.
- Prefix length: $p = 32 - 8 = 24$ (`/24`).
- Usable hosts: $2^8 - 2 = 256 - 2 = 254$.
- Netmask: `255.255.255.0`.
- Starting address: `10.20.4.0`.
- Network address: `10.20.4.0/24`.
- Address span: `10.20.4.0` to `10.20.4.255`.
- Usable host range: `10.20.4.1` through `10.20.4.254`.
- Broadcast address: `10.20.4.255`.
- Next available block starts at: `10.20.5.0`.

### Subnet 3: `data` (Requirement: 100 hosts)
- Minimum addresses needed: $100 + 2 = 102$.
- Smallest power of 2: $2^7 = 128 \ge 102$.
- Host bits: $h = 7$.
- Prefix length: $p = 32 - 7 = 25$ (`/25`).
- Usable hosts: $2^7 - 2 = 128 - 2 = 126$.
- Netmask: `255.255.255.128`.
- Starting address: `10.20.5.0`.
- Network address: `10.20.5.0/25`.
- Address span: `10.20.5.0` to `10.20.5.127`.
- Usable host range: `10.20.5.1` through `10.20.5.126`.
- Broadcast address: `10.20.5.127`.
- Next available block starts at: `10.20.5.128`.

### Subnet 4: `management` (Requirement: 20 hosts)
- Minimum addresses needed: $20 + 2 = 22$.
- Smallest power of 2: $2^5 = 32 \ge 22$.
- Host bits: $h = 5$.
- Prefix length: $p = 32 - 5 = 27$ (`/27`).
- Usable hosts: $2^5 - 2 = 32 - 2 = 30$.
- Netmask: `255.255.255.224`.
- Starting address: `10.20.5.128`.
- Network address: `10.20.5.128/27`.
- Address span: `10.20.5.128` to `10.20.5.159`.
- Usable host range: `10.20.5.129` through `10.20.5.158`.
- Broadcast address: `10.20.5.159`.
- Remaining address space in `10.20.0.0/16` starts at `10.20.5.160`.

---

## 3. Stateless NACL Reasoning

### Why a Stateless NACL Needs Separate Rules for Reply Traffic
Unlike stateful firewalls (such as AWS Security Groups or iptables `conntrack`), a stateless Network Access Control List (NACL) evaluates every packet independently in complete isolation. It maintains no connection state table and has no concept of an established session, TCP 3-way handshake, or session lifetime. 

When a client initiates an inbound TCP connection to the public load balancer on port 80 or 443, the client sends an initial SYN packet from an ephemeral source port (1024–65535) destined to port 80/443. The inbound NACL rule allows this incoming packet. However, when the load balancer generates the TCP SYN-ACK or data response packet, this response is evaluated by the **outbound** NACL rules as an independent packet whose destination IP is the client's address and destination port is the client's ephemeral port (1024–65535). Because the NACL cannot remember that this packet is a reply to an already-allowed inbound request, an explicit outbound rule permitting traffic to ephemeral ports (1024–65535) is strictly required; otherwise, the reply packet is dropped by the default outbound deny rule.

Similarly, when the public load balancer forwards requests outbound to the backend application servers in the `app` subnet on TCP port 8000, the app servers' replies travel back inbound from `10.20.0.0/22` to the load balancer's ephemeral ports. An explicit inbound rule allowing traffic from `10.20.0.0/22` on destination ports 1024–65535 must exist to permit these backend responses.

### Why Rule Ordering Matters for `198.51.100.0/24`
NACL rules are processed in strict ascending numerical order (lowest rule number first), and evaluation stops on the **first matching rule** (first-match-wins semantics). 

The address range `198.51.100.0/24` is a subset of the global internet (`0.0.0.0/0`). If the allow rules for web traffic (e.g., allowing TCP 80/443 from `0.0.0.0/0`) were assigned lower rule numbers (e.g., rule 100) than the deny rule for `198.51.100.0/24` (e.g., rule 300), an inbound packet from an abusive IP such as `198.51.100.9` targeting port 443 would match rule 100 first and be allowed through. The deny rule at rule 300 would never be evaluated.

To effectively block all traffic from the abusive range `198.51.100.0/24`—including traffic destined for legitimate web ports (80 and 443)—the deny rule must be given a **lower rule number** (Rule 100) than the broad allow rules (Rules 200 and 210). This ensures the packet is matched and dropped immediately before any broader allow rule can take effect.

