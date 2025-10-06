response = self.client.get("/subscriptions/")
self.assertEqual(response.status_code, 200)
self.assertContains(response, "Alice")
