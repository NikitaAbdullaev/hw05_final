import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from ..models import Group, Follow, Post, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='test_group',
            description='test_group_description',
            slug='test_slug'
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )

        cls.wrong_user = User.objects.create_user(username='wrong_test_user')
        cls.wrong_group = Group.objects.create(
            title='wrong_test_group',
            description='wrong_test_group_description',
            slug='wrong_test_slug'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон"""
        slug = self.group.slug
        username = self.user.username
        post_id = self.post.id
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': slug}): (
                'posts/group_list.html'
            ),
            reverse('posts:profile', kwargs={'username': username}): (
                'posts/profile.html'
            ),
            reverse('posts:post_detail', kwargs={'post_id': post_id}): (
                'posts/post_detail.html'
            ),
            reverse('posts:post_edit', kwargs={'post_id': post_id}): (
                'posts/create_post.html'
            ),
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_user.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_user.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        first_object_values = {
            first_object.author.username: self.user.username,
            first_object.text: self.post.text,
            first_object.group.title: self.post.group.title,
            first_object.image: self.post.image,
        }
        for value, expected in first_object_values.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

    def test_group_posts_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        # Создаем дополнительные посты с другой группой
        for n in range(5):
            Post.objects.create(
                text=f'Тестовый текст {n}',
                author=self.user,
                group=self.wrong_group
            )
        # Получаем список постов
        slug = self.group.slug
        response = self.authorized_user.get(
            reverse('posts:group_list', kwargs={'slug': slug})
        )
        objects = response.context['page_obj'].object_list
        # Утверждаем, что в контекст передались лишь те посты, название
        # группы которых совпадает с запрашиваемым.
        # Утверждаем, что картинка выведенного поста, совпадает с
        # той, что находится в базе.
        for object in objects:
            with self.subTest(object=object):
                self.assertEqual(object.group.title, self.group.title)
                self.assertEqual(object.image, self.post.image)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        # Создаем дополнительные посты с другим автором
        for n in range(5):
            Post.objects.create(
                text=f'Тестовый текст {n}',
                author=self.wrong_user,
                group=self.group
            )
        # Получаем список постов
        username = self.user.username
        response = self.authorized_user.get(
            reverse('posts:profile', kwargs={'username': username})
        )
        objects = response.context['page_obj'].object_list
        # Утверждаем, что в контекст передались лишь те посты, юзернейм
        # автора которых совпадает с запрашиваемым.
        # Утверждаем, что картинка выведенного поста, совпадает с
        # той, что находится в базе.
        for object in objects:
            with self.subTest(object=object):
                self.assertEqual(object.author.username, username)
                self.assertEqual(object.image, self.post.image)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        # Создаем дополнительный пост, с другим айди
        Post.objects.create(
            text='Wrong тестовый текст',
            author=self.user,
            group=self.group
        )
        post_id = self.post.id
        response = self.authorized_user.get(
            reverse('posts:post_detail', kwargs={'post_id': post_id})
        )
        # Утверждаем, что в контекст передался именно тот пост, айди которого
        # совпадает с запрашиваемым.
        # Утверждаем, что картинка выведенного поста, совпадает с
        # той, что находится в базе.
        self.assertEqual(response.context['post'].id, post_id)
        self.assertEqual(response.context['post'].image, self.post.image)

        form_data = {
            'text': 'тестовый текст комментария',
        }
        self.authorized_user.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        new_response = self.authorized_user.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        comment = new_response.context['comments'].first()
        # Утверждаем, что текст созданного коментария совпадает
        # с тем, который передается в шаблон.
        self.assertEqual(comment.text, form_data['text'])

    def test_create_post_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_user.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_user.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

        # Проверяем, что в форму переданы нужные значения редактируемого поста
        text_field_value = response.context['form'].instance.text
        self.assertEqual(text_field_value, self.post.text)

        group_field_value = response.context['form'].instance.group
        self.assertEqual(group_field_value, self.post.group)

    def test_index_page_cashe(self):
        """Проверка кеширования главной страницы."""
        response = self.authorized_user.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            text='test_new_post',
            author=self.user,
        )
        response_old = self.authorized_user.get(reverse('posts:index'))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.authorized_user.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertNotEqual(old_posts, new_posts)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='test_group',
            description='test_group_description',
            slug='test_slug'
        )
        for i in range(13):
            cls.post = Post.objects.create(
                text=f'Тестовый текст {i}',
                author=cls.user,
                group=cls.group
            )

    def setUp(self):
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)
        self.reversed_urls = {
            'posts:index': None,
            'posts:group_list': {'slug': self.group.slug},
            'posts:profile': {'username': self.user.username},
        }

    def test_first_page_contains_ten_records(self):
        for reversed_url, maskurl in self.reversed_urls.items():
            with self.subTest(reversed_url=reversed_url):
                response = self.client.get(
                    reverse(reversed_url, kwargs=maskurl)
                )
                self.assertEqual(
                    len(response.context['page_obj'].object_list), 10
                )

    def test_second_page_contains_three_records(self):
        for reversed_url, maskurl in self.reversed_urls.items():
            with self.subTest(reversed_url=reversed_url):
                response = self.client.get(
                    reverse(reversed_url, kwargs=maskurl) + '?page=2'
                )
                self.assertEqual(
                    len(response.context['page_obj'].object_list), 3
                )


class CreationPostTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='test_group',
            description='test_group_description',
            slug='test_slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )
        cls.reversed_urls = {
            'posts:index': None,
            'posts:group_list': {'slug': cls.group.slug},
            'posts:profile': {'username': cls.user.username},
        }

    def setUp(self):
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_post_added_correctly(self):
        """
        При создании поста с указанием группы, он добавляется
        на главной странице, на странице выбранной группы,
        в профайле пользователя.
        """
        for reversed_url, maskurl in self.reversed_urls.items():
            with self.subTest(reversed_url=reversed_url):
                response = self.authorized_user.get(
                    reverse(reversed_url, kwargs=maskurl)
                )
                self.assertIn(
                    self.post,
                    response.context['page_obj']
                )

    def test_post_not_added_to_wrong_group(self):
        """
        Созданный пост не попадает в группу, для которой не был предназначен.
        """
        wrong_group = Group.objects.create(
            title='wrong_test_group',
            description='wrong_test_group_description',
            slug='wrong_test_slug'
        )
        self.assertEqual(wrong_group.posts.count(), 0)


class FollowingTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='user')
        cls.user_2 = User.objects.create_user(username='user2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый текст'
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_authorized_client_can_subscribe_and_unsubscribe(self):
        """
        Авторизованный пользователь может подписываться на других пользователей
        и удалять их из подписок.
        """
        self.authorized_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post.author}
            )
        )
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(Follow.objects.last().author, self.author)
        self.assertEqual(Follow.objects.last().user, self.user)

        self.authorized_client.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.post.author}
            )
        )
        self.assertEqual(Follow.objects.count(), 0)

    def test_authorized_client_can_subscribe_and_unsubscribe(self):
        """
        Новая запись пользователя появляется в ленте тех, кто на него
        подписан и не появляется в ленте тех, кто не подписан.
        """
        # Создаем второй клиент, который не будет подписан на автора
        authorized_client_2 = Client()
        authorized_client_2.force_login(self.user_2)
        # Подписываем на автора первый клиент
        self.authorized_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.post.author}
            )
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        response_2 = authorized_client_2.get(reverse('posts:follow_index'))
        self.assertEqual(response.context['page_obj'][0].text, self.post.text)
        self.assertEqual(len(response_2.context['page_obj']), 0)
