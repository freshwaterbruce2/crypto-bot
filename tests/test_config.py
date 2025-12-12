from src.config.config import Config


def test_config_env_fallback(monkeypatch):
    monkeypatch.delenv("KRAKEN_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_API_SECRET", raising=False)

    cfg = Config(api_key="explicit-key", api_secret="explicit-secret")

    assert cfg.api_key == "explicit-key"
    assert cfg.api_secret == "explicit-secret"

    monkeypatch.setenv("KRAKEN_API_KEY", "env-key")
    monkeypatch.setenv("KRAKEN_API_SECRET", "env-secret")

    cfg_env = Config()
    assert cfg_env.api_key == "env-key"
    assert cfg_env.api_secret == "env-secret"


def test_config_validation_rules():
    cfg = Config()
    assert cfg.validate() is True

    cfg_invalid = Config(rsi_oversold=60, rsi_overbought=40)
    assert cfg_invalid.validate() is False


def test_config_to_dict_roundtrip():
    cfg = Config(trading_pairs=["BTC/USD"], max_open_positions=10)
    cfg_dict = cfg.to_dict()

    recreated = Config.from_dict(cfg_dict)
    assert recreated.trading_pairs == ["BTC/USD"]
    assert recreated.max_open_positions == 10
