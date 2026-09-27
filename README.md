# my_own_namespace.yandex_cloud_elk

Коллекция Ansible для создания текстовых файлов на удалённых хостах с автоматическим созданием недостающих каталогов.

## Содержимое коллекции

### Модули

| Модуль | Описание |
|---|---|
| `my_own_module` | Создаёт текстовый файл по заданному пути с заданным содержимым |

### Роли

| Роль | Описание |
|---|---|
| `test_role` | Тестовая роль для проверки работы модуля `my_own_module` |

## Требования

- Ansible 2.23.0+
- Python 3.14.4+ на управляемых хостах

## Установка

```bash
ansible-galaxy collection build
ansible-galaxy collection install my_own_namespace-yandex_cloud_elk-1.0.0.tar.gz
```


## Использование

### Модуль `my_own_module`

```yaml
- name: Create a text file
  my_own_namespace.yandex_cloud_elk.my_own_module:
    path: /tmp/ansible_test/file.txt
    content: "Hello from collection!\n"
```


### Роль `test_role`

```yaml
- name: Play for module testing
  hosts: localhost
  connection: local
  roles:
    - role: my_own_namespace.yandex_cloud_elk.test_role
      vars:
        path: /tmp/ansible_test/test.txt
        content: "Hello from created role!\n"
```

## Лицензия

MIT

## Автор

Berko Alex (@AlexBerko)