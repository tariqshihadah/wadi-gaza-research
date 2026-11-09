from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pytest

from change_ci.config import AnalysisConfig
from index_ci.config import IndexAnalysisConfig


@pytest.fixture
def analysis_config_factory() -> Callable[..., AnalysisConfig]:
    root = Path(__file__).resolve().parents[1]
    base_config = AnalysisConfig.from_yaml(
        root / "configs" / "change_ci.yaml", project_root=root
    )

    def create_config(data_root: Path, output_dir: Path, **overrides: Any) -> AnalysisConfig:
        return replace(
            base_config,
            data_root=data_root,
            output_dir=output_dir,
            **overrides,
        )

    return create_config


@pytest.fixture
def index_config_factory() -> Callable[..., IndexAnalysisConfig]:
    root = Path(__file__).resolve().parents[1]
    base_config = IndexAnalysisConfig.from_yaml(
        root / "configs" / "index_ci.yaml", project_root=root
    )

    def create_config(
        data_root: Path, output_dir: Path, **overrides: Any
    ) -> IndexAnalysisConfig:
        return replace(
            base_config,
            data_root=data_root,
            output_dir=output_dir,
            **overrides,
        )

    return create_config
