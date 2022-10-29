from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author_user = User.objects.create_user(username='post_author_user')
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='test_group',
            description='test_group_description',
            slug='test_slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            pub_date='2000-01-01 00:00:00',
            author=cls.author_user,
            group=cls.group
        )

    def setUp(self):
        cache.clear()
        # авторизуемся как пользователь – автор поста
        self.author_authorized_client = Client()
        self.author_authorized_client.force_login(self.author_user)
        # авторизуемся как пользователь
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_exist_at_desired_location(self):
        """
        Cтраницы /, /group/<slug>/, /profile/<username>/, /posts/<post_id>/
        доступны всем пользователям.
        """
        urls = ['/',
                f'/group/{self.group.slug}/',
                f'/profile/{self.user.username}/',
                f'/posts/{self.post.id}/']
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_404_page(self):
        """
        Запрос к несуществующей странице /unexisting_page/
        возвращает ошибку 404 и отображает кастомную страницу ошибки.
        """
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_create_url_redirects_anonymous_user_on_login_page(self):
        """
        Страница по адресу /create/ перенаправит анонимного пользователя
        на страницу авторизации.
        """
        response = self.client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit_url_redirects_users_except_author(self):
        """
        Страница по адресу /posts/<post_id>/edit/ перенаправит всех
        авторизованных пользователей, кроме автора записи,
        на страницу /posts/<post_id>/; неавторизованные пользователи будут
        перенаправлены на страницу авторизации.
        """
        post_id = self.post.id
        url = f'/posts/{post_id}/edit/'
        auth_response = self.authorized_client.get(url, follow=True)
        guest_response = self.client.get(url, follow=True)
        self.assertRedirects(
            auth_response, f'/posts/{post_id}/'
        )
        self.assertRedirects(
            guest_response, f'/auth/login/?next=/posts/{post_id}/edit/'
        )

    def test_urls_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for url, template in templates.items():
            with self.subTest(url=url):
                response = self.author_authorized_client.get(url)
                self.assertTemplateUsed(response, template)
