# Running a Cathedral Miner

Cathedral now has two miner tracks:

1. Compute miners provide machines that validators can inspect.
2. Regulatory intelligence miners run Hermes workers on Polaris and maintain country cards.

For the regulatory worker path, start here: [docs/regulatory-intelligence/miner.md](regulatory-intelligence/miner.md).

This guide gets you from zero to a registered miner on Cathedral (Bittensor Subnet 39) in roughly an hour. It assumes you already have a Bittensor wallet and an SSH-accessible GPU box.

> **Status:** Cathedral is early. Weight-setting is currently blocked on validator stake. Miners can register, pass verification, and accumulate CUs, but emissions won't flow until the stake threshold is met. See [docs/policy.md](policy.md).

## What you need

Three things, on separate hosts (or the same host for a minimal setup):

1. **A registered hotkey on SN39.** Use `btcli` to register. The hotkey's coldkey pays the registration fee.
2. **A compute node.** A Linux box with SSH access. GPU nodes need NVIDIA drivers, CUDA, and Docker. CPU nodes need normal shell access.
3. **A miner host.** A CPU-only Linux box that runs the `cathedral-miner` process. This is what registers your node with validators and holds your hotkey. Cheap VPS is fine.

The miner host discovers validators from the SN39 metagraph, connects to the selected validator over gRPC, and connects to your compute node over SSH.

## Validator discovery

Miners do not need a hardcoded Cathedral operator endpoint. The miner reads validators from the SN39 metagraph, selects one by the configured assignment strategy, reads that validator's on-chain axon host, then constructs the bid endpoint as:

```text
http://<validator-axon-host>:50052
```

That means validators who want miner traffic must publish an axon on chain and expose TCP `50052` on the same host. The miner's default `bid_grpc_port = 50052` is the subnet convention.

## Configure the miner

Create `miner.toml`:

```toml
bid_grpc_port = 50052

[bittensor]
wallet_name = "your_wallet"
hotkey_name = "your_hotkey"
network = "finney"
netuid = 39
chain_endpoint = "wss://entrypoint-finney.opentensor.ai:443"
axon_port = 50051

[database]
url = "sqlite:/opt/cathedral/data/miner.db?mode=rwc"

[node_management]
nodes = [
    { host = "<your.gpu.node.ip>", port = 22, username = "root", gpu_category = "RTX_5090", gpu_count = 1 },
]

[ssh_session]
miner_node_key_path = "/root/.ssh/your_ssh_key"
default_node_username = "root"

[validator_assignment]
strategy = "highest_stake"

[bidding.strategy.static.static_prices]
RTX_5090 = 0.45
```

### Key fields

- **`node_management.nodes`** — your GPU nodes. `host` must be an IPv4 literal, not a hostname. `gpu_category` must match what Cathedral's incentive config supports.
- **`ssh_session.miner_node_key_path`** — path to the SSH **private key** on the miner host. The public key must be in the GPU node's `authorized_keys`.
- **`validator_assignment.strategy`**: use `highest_stake` for normal mining. `fixed_assignment` and `grpc_endpoint_override` are for local debugging or explicit validator tests, not the public path.
- **`bidding.strategy.static.static_prices`** — USD per GPU per hour. Set just above your cost.

## Build the binary

On any x86_64 Linux box:

```bash
apt-get install -y protobuf-compiler pkg-config libssl-dev build-essential
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env
git clone https://github.com/bigailabs/cathedral.git
cd cathedral
cargo build --release --package basilica-miner
```

Binary lands at `target/release/cathedral-miner`.

## Run

```bash
mkdir -p /opt/cathedral/data /opt/cathedral/config
cp miner.toml /opt/cathedral/config/
cp target/release/cathedral-miner /opt/cathedral/bin/
/opt/cathedral/bin/cathedral-miner --config /opt/cathedral/config/miner.toml
```

For long-running operation, use tmux, systemd, or Docker — see the [legacy setup guide](https://github.com/one-covenant/basilica/blob/main/basilica/docs/miner.md) for systemd and Docker templates (crate names differ but the patterns transfer).

## Verify it's working

You should see in the miner logs:

```
INFO cathedral_miner::registration_client: Successfully registered with validator registration_id=reg-...  has_ssh_key=true
INFO cathedral_miner::node_manager: Deployed SSH keys for validator on 1 nodes
INFO cathedral_miner::bidding: Starting lifecycle loop: health_check=60s
```

If the selected validator accepts, your node will be scored on the next verification cycle, usually within 10 minutes. You can also watch the miner logs for `Successfully registered with validator`.

Discovery uses the validator's on-chain axon host plus `bid_grpc_port`. If bid registration fails with connection refused, the selected validator is not exposing TCP `50052` or you are using a stale fixed endpoint.

## How verification works

Every 10 minutes, the validator SSHes into your GPU node and runs:

- **SSH liveness** — can it connect
- **Hardware profile** — `lshw` via SSH
- **Network profile** — geolocation, ISP
- **Speedtest** — download and upload bandwidth
- **Docker check** — version, can pull CUDA image
- **Storage check** — filesystem accessibility
- **NAT check** — inbound reachability
- **GPU discovery** — `nvidia-smi` to get GPU count, names, UUIDs

If all pass, the node enters the availability log with `is_available=1`. The CU generator (hourly tick) reads the availability log and posts CU records to the incentive API.

## Pricing

`[bidding.strategy.static.static_prices]` sets your ask in USD per GPU per hour. The validator enforces a **bid floor** of ~10% below the baseline CU rate for the category. Setting a price below the floor will cause the validator to reject your bid.

Current category base rates (from `api.polaris.computer/v1/incentive/config`):

| Category | CU rate (per GPU-hr) | Notes |
|---|---|---|
| A100 | $0.15 | 1x target, 8 GPUs total |
| H100 | $1.10 | 1x target, 8 GPUs total |

Targets will rise as the network grows. See [docs/policy.md](policy.md) for how the incentive mechanism works.

## Troubleshooting

**"unknown miner_hotkey" on RegisterBid** — the validator's local metagraph cache hasn't picked up your registration yet. Wait for the next verification tick (~10 min) or restart the validator.

**Node goes to `offline` status** — usually SSH connectivity, NAT, or the validator can't run `nvidia-smi` on your node. Check the validator's logs for which check failed.

**Verification score stays at 0** — ensure at least one validation cycle completed with all checks green. Check `gpu_uuid_assignments` on the validator side.

**Need help** — open an issue on [bigailabs/cathedral](https://github.com/bigailabs/cathedral/issues) or DM a maintainer.

## Next

- Read [docs/policy.md](policy.md) to understand how CUs and RUs turn into emissions
- Read [docs/validator.md](validator.md) to understand what the validator checks
- Read [docs/architecture.md](architecture.md) for the system overview
