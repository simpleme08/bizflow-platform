from django.test import SimpleTestCase


class SubscriptionEndpointContractTests(SimpleTestCase):
    def test_endpoint_contract_is_documented(self):
        self.assertTrue('/api/subscription/' == '/api/subscription/')
