from hashlib import sha256
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
from clinica.models import EventoSeguridadOWASP


class SessionAndFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_clinica', verbosity=0)

    def test_home_uses_current_asset_versions_and_disables_stale_cache(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        for path in ('js/api.js', 'js/app.js', 'js/validators.js', 'css/app.css'):
            digest = sha256((settings.FRONTEND_DIR / path).read_bytes()).hexdigest()[:16]
            url = f'/{path}?v={digest}'
            self.assertContains(response, url)
            asset = self.client.get(url)
            self.assertEqual(asset.status_code, 200)
            self.assertIn('no-store', asset['Cache-Control'])
            self.assertTrue(b''.join(asset.streaming_content))

    def test_normal_login_logout_and_repeated_logout_with_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.get('/api/v1/auth/csrf/')
        login = client.post('/api/v1/auth/login/', {'username':'diego.astudillo','password':'TallerPC!26'},
            format='json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(login.status_code,200)
        self.assertTrue(client.get('/api/v1/auth/me/').data['authenticated'])
        self.assertEqual(client.post('/api/v1/auth/logout/',{},format='json',
            HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code,200)
        count = EventoSeguridadOWASP.objects.filter(evento='LOGOUT').count()
        self.assertEqual(client.post('/api/v1/auth/logout/',{},format='json',
            HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code,200)
        self.assertEqual(EventoSeguridadOWASP.objects.filter(evento='LOGOUT').count(),count)
        self.assertFalse(client.get('/api/v1/auth/me/').data['authenticated'])
        self.assertEqual(client.get('/api/v1/fichas/').status_code,403)

    def test_authenticated_logout_still_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.login(username='diego.astudillo',password='TallerPC!26')
        self.assertEqual(client.post('/api/v1/auth/logout/',{},format='json').status_code,403)
        self.assertTrue(client.get('/api/v1/auth/me/').data['authenticated'])
