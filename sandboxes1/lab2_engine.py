"""
Real federated-learning engine for lab2 (MedSync). A real logistic-regression
model is trained with real gradient descent across 5 simulated hospital
nodes and aggregated with real FedAvg -- no lookup tables. Node 3's label
flip and gradient-boosting attack genuinely shifts the aggregated decision
boundary and genuinely drops measured accuracy on a held-out test set.
"""
import numpy as np

N_NODES = 5
FEATURES = 4
LR = 0.6
LOCAL_STEPS = 25
RARE_PREVALENCE = 0.12


def _rng(seed):
    return np.random.RandomState(seed)


def build_dataset(seed=7):
    """Two-class synthetic diagnostic dataset: common_condition (0) vs rare_condition (1)."""
    rng = _rng(seed)
    n_total = 4000
    n_rare = int(n_total * RARE_PREVALENCE)
    n_common = n_total - n_rare
    mean_common = np.array([0.0, 0.0, 0.0, 0.0])
    mean_rare = np.array([2.4, 2.0, -1.2, 1.6])
    X_common = rng.normal(mean_common, 1.0, size=(n_common, FEATURES))
    X_rare = rng.normal(mean_rare, 1.1, size=(n_rare, FEATURES))
    X = np.vstack([X_common, X_rare])
    y = np.concatenate([np.zeros(n_common), np.ones(n_rare)])
    idx = rng.permutation(len(X))
    X, y = X[idx], y[idx]
    split = int(len(X) * 0.8)
    return {"X_train": X[:split], "y_train": y[:split], "X_test": X[split:], "y_test": y[split:]}


def partition_nodes(data, seed=11):
    """Split training data IID across N_NODES hospital nodes."""
    rng = _rng(seed)
    idx = rng.permutation(len(data["X_train"]))
    chunks = np.array_split(idx, N_NODES)
    return [{"X": data["X_train"][c], "y": data["y_train"][c]} for c in chunks]


def _sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))


def _grad(w, X, y):
    z = X @ w
    p = _sigmoid(z)
    return X.T @ (p - y) / len(y)


def local_update(w, node, steps=LOCAL_STEPS, lr=LR):
    """Run real local gradient descent on this node's data; return the net weight delta."""
    w0 = w.copy()
    wl = w.copy()
    Xb = np.hstack([node["X"], np.ones((len(node["X"]), 1))])
    for _ in range(steps):
        g = _grad(wl, Xb, node["y"])
        wl -= lr * g
    return wl - w0  # the "gradient update" this node sends


def poisoned_update(w, node, flip_frac=0.95, boost=20.0, steps=LOCAL_STEPS, lr=LR):
    """Label-flip a fraction of this node's rare_condition labels, then boost the resulting delta."""
    y = node["y"].copy()
    rare_idx = np.where(y == 1)[0]
    rng = np.random.RandomState(99)
    n_flip = int(len(rare_idx) * flip_frac)
    flip_idx = rng.choice(rare_idx, size=n_flip, replace=False) if n_flip else np.array([], dtype=int)
    y[flip_idx] = 0
    poisoned_node = {"X": node["X"], "y": y}
    delta = local_update(w, poisoned_node, steps=steps, lr=lr)
    return delta * boost


def fedavg(w, deltas):
    return w + np.mean(deltas, axis=0)


def trimmed_mean(w, deltas, drop=1):
    """Coordinate-wise: drop the `drop` largest-magnitude updates, average the rest."""
    norms = [np.linalg.norm(d) for d in deltas]
    order = np.argsort(norms)
    keep = [deltas[i] for i in order[:len(deltas) - drop]]
    return w + np.mean(keep, axis=0)


def accuracy(w, data, subgroup=None):
    X = data["X_test"]
    y = data["y_test"]
    if subgroup == "rare":
        mask = y == 1
        X, y = X[mask], y[mask]
    Xb = np.hstack([X, np.ones((len(X), 1))])
    pred = (_sigmoid(Xb @ w) >= 0.5).astype(float)
    return float(np.mean(pred == y)) if len(y) else 0.0


def init_model():
    return np.zeros(FEATURES + 1)


def train_rounds(data, nodes, n_rounds, poison_round=None, agg="fedavg"):
    """Run n_rounds of real federated training; optionally poison node 3 at poison_round."""
    w = init_model()
    history = []
    for r in range(1, n_rounds + 1):
        deltas = []
        for i, node in enumerate(nodes):
            if poison_round is not None and r == poison_round and i == 2:
                deltas.append(poisoned_update(w, node))
            else:
                deltas.append(local_update(w, node))
        if agg == "trimmed_mean":
            w = trimmed_mean(w, deltas)
        else:
            w = fedavg(w, deltas)
        history.append({"round": r, "w": w.copy(), "deltas": deltas,
                        "acc": accuracy(w, data), "rare_acc": accuracy(w, data, subgroup="rare")})
    return history
