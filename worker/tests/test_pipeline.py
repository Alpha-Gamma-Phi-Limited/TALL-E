from worker.adapters.bargain_chemist import BargainChemistFixtureAdapter
from worker.adapters.mecca import MeccaFixtureAdapter
from worker.adapters.pb_tech import PBTechFixtureAdapter
from worker.pipeline import IngestionPipeline
from worker.models import LatestPrice, Product, RetailerProduct


def test_pipeline_ingests_fixture(session):
    pipeline = IngestionPipeline(session, PBTechFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    assert session.query(Product).count() >= 1
    assert session.query(RetailerProduct).count() >= 1
    assert session.query(LatestPrice).count() >= 1


def test_pipeline_ingests_pharma_fixture(session):
    pipeline = IngestionPipeline(session, BargainChemistFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    product = session.query(Product).filter(Product.vertical == "pharma").first()
    assert product is not None


def test_pipeline_ingests_beauty_fixture(session):
    pipeline = IngestionPipeline(session, MeccaFixtureAdapter())
    run = pipeline.run()

    assert run.status == "completed"
    assert run.items_total > 0
    product = session.query(Product).filter(Product.vertical == "beauty").first()
    assert product is not None
