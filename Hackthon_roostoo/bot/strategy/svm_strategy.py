import numpy as np
from sklearn.svm import SVC
from typing import List, Tuple


def sma(series: List[float], window: int) -> List[float]:
    if len(series) < window:
        return []
    return [sum(series[i-window:i]) / window for i in range(window, len(series)+1)]


def build_sma_features(closes: List[float]) -> Tuple[np.ndarray, np.ndarray]:
    if len(closes) < 15:
        return np.zeros((0, 3)), np.zeros((0,))
    sma3 = sma(closes, 3)
    sma10 = sma(closes, 10)
    features, labels = [], []
    # Align with lagging windows
    min_len = min(len(sma3), len(sma10))
    for i in range(min_len - 1):
        idx3 = i + (len(sma3) - min_len)
        idx10 = i + (len(sma10) - min_len)
        close_idx = i + 10
        if close_idx + 1 >= len(closes):
            break
        momentum = (closes[close_idx] - closes[close_idx-1]) / closes[close_idx-1]
        features.append([sma3[idx3], sma10[idx10], momentum])
        labels.append(1 if closes[close_idx+1] > closes[close_idx] else 0)
    return np.array(features), np.array(labels)


def train_svm(features: np.ndarray, labels: np.ndarray) -> SVC:
    model = SVC(probability=True, kernel='rbf', gamma='scale', C=1.0)
    model.fit(features, labels)
    return model


def predict_signal(model: SVC, current_feature: List[float]) -> str:
    pred = model.predict([current_feature])[0]
    return 'BUY' if pred == 1 else 'SELL'
