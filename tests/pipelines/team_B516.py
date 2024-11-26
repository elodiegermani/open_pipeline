from pathlib import Path

from narps_open.pipelines.team_X19V_new import PipelineTeamX19V


def root_dir():
    return Path(__file__).parent.parent.parent


def events_file():
    return (
        root_dir
        / "data"
        / "original"
        / "ds001734"
        / "sub-001"
        / "func"
        / "sub-001_task-MGT_run-01_events.tsv"
    )


def test_constructor():
    pipeline = PipelineTeamX19V()

    assert pipeline.fwhm == 5.0
    assert pipeline.team_id == "X19V"
    assert pipeline.contrast_list == ["0001", "0002", "0003"]


def test_get_session_infos():
    pipeline = PipelineTeamX19V()

    assert pipeline