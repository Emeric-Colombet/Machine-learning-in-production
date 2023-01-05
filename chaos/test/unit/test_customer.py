import pytest
from chaos.domain.customer import Customer
from interpret.glassbox.ebm.ebm import ExplainableBoostingClassifier
from unittest import TestCase
from churn.domain.churn_model import ChurnModelFinal
from chaos.infrastructure.customer_loader import CustomerLoader


def do_nothing(self):
    pass


class TestModel(object):

    def test_model_loading(self):
        """ Here we check if the Customer will load the ChurnModel, and if it's
        pipeline contain the ExplainableBoostingClassifier"""
        customer = Customer(marketing={"A": 1},
                            model=ChurnModelFinal.load())
        assert isinstance(
            customer.model.pipe.get_params()['classifier'],
            ExplainableBoostingClassifier)

    @pytest.mark.parametrize(
        "marketing, expected",
        [({"BALANCE": 93259.57, "NB_PRODUITS": 3, "CARTE_CREDIT": "Yes",
           "SALAIRE": 141035.65, "SCORE_CREDIT": 581.0,
           "DATE_ENTREE": "2015-01-01 00:00:00", "NOM": "Mazzi",
           "PAYS": "Allemagne", "SEXE": "F", "AGE": 43,
           "MEMBRE_ACTIF": "No"}, True)])
    def test_model_prediction(self, marketing, expected):
        """ Here we provide an object corresponding to a customer, and we
                verify that the prediction worked, and that the output is True.
        """

        customer = Customer(marketing, ChurnModelFinal.load())
        predict_proba_serie = customer.predict_subscription()
        TestCase().assertTrue((predict_proba_serie.values[0] > 0.5) == expected)


class TestCustomerLoader:
    def test_customer_loader(self, mock_connexion):
        """ We can init a CustomerLoader instance who need a connection, \
            but we have mocked it thanks to the function mock_connect """
        customer_loader = CustomerLoader()
        assert isinstance(customer_loader, CustomerLoader)
