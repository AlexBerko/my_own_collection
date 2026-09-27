# my_own_namespace.yandex_cloud_elk

Коллекция Ansible для создания текстовых файлов, управления виртуальными машинами в Yandex Cloud и развёртывания Observability-стека (ClickHouse, Vector, Lighthouse).

## Содержимое коллекции

### Модули

| Модуль | Описание |
|---|---|
| `my_own_module` | Создаёт текстовый файл по заданному пути с заданным содержимым, автоматически создавая недостающие каталоги |
| `yc_vm` | Создаёт, удаляет и управляет ВМ в Yandex Cloud на основе образа семейства Rocky Linux |

### Роли

| Роль | Описание |
|---|---|
| `test_role` | Тестовая роль для проверки работы модуля `my_own_module` |
| `clickhouse` | Установка и настройка ClickHouse (форк [AlexeySetevoi/ansible-clickhouse](https://github.com/AlexeySetevoi/ansible-clickhouse), см. раздел ниже) |
| `vector` | Установка и настройка Vector для сбора и отправки логов |
| `lighthouse` | Установка и настройка веб-интерфейса Lighthouse для ClickHouse |

## Требования

- Ansible Core 2.16+
- Python 3.10+
- Для модуля `yc_vm`:
  - Python-пакет `yandex-cloud` (`pip install git+https://github.com/yandex-cloud/python-sdk`)
  - Переменная окружения `YC_IAM_TOKEN` с действующим IAM-токеном
  - Настроенный `yc` CLI для получения `folder_id` и `subnet_id`
- Для роли `clickhouse`:
  - Коллекция `community.general` (`ansible-galaxy collection install community.general`)

- Для работы с динамически создаваемыми ВМ - отключить проверку SSH-ключей хостов:
  создать `ansible.cfg` рядом с playbook со следующим содержимым:

  ```ini
  [defaults]
  host_key_checking = False
  ```

## Установка

```bash
ansible-galaxy collection build
ansible-galaxy collection install my_own_namespace-yandex_cloud_elk-1.0.1.tar.gz -p ./collections --force
```

### Установка зависимостей ролей

```bash
cd collections/ansible_collections/my_own_namespace/yandex_cloud_elk
ansible-galaxy install -r requirements.yml -p roles/
ansible-galaxy collection install community.general
```

## Использование

### Модуль `my_own_module`

```yaml
- name: Create a text file
  my_own_namespace.yandex_cloud_elk.my_own_module:
    path: /tmp/ansible_test/file.txt
    content: "Hello from collection!\n"
```

### Модуль `yc_vm`

Перед использованием экспортируй IAM-токен:

```bash
export YC_IAM_TOKEN=$(yc iam create-token)
```

Пример создания прерываемой ВМ с Rocky Linux 10 и добавления её в динамический inventory:

```yaml
- name: Create a Rocky Linux 10 VM
  hosts: localhost
  gather_facts: false

  tasks:
    - name: Create VM
      my_own_namespace.yandex_cloud_elk.yc_vm:
        folder_id: "b1gxxxxxxxxxxxxxxxx"
        name: "rocky-vm"
        zone: "ru-central1-a"
        subnet_id: "e9bxxxxxxxxxxxxxxxx"
        image_family: "rocky-10"
        cores: 2
        memory: 2
        core_fraction: 20
        disk_size: 10
        disk_type: "network-hdd"
        preemptible: true
        username: "alex"
        ssh_key: "{{ lookup('file', '~/.ssh/id_rsa.pub') }}"
        state: present
      register: vm_result

    - name: Add VM to dynamic inventory
      ansible.builtin.add_host:
        name: "{{ vm_result.vm.name }}"
        ansible_host: "{{ vm_result.vm.external_ip }}"
        ansible_user: "alex"
        ansible_ssh_private_key_file: "~/.ssh/id_rsa"
        groups: observability
```

#### Параметры модуля `yc_vm`

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `folder_id` | str | - | ID каталога Yandex Cloud (обязательно) |
| `name` | str | - | Имя ВМ (обязательно) |
| `zone` | str | `ru-central1-a` | Зона: `ru-central1-a`, `-b`, `-d`, `-e` |
| `subnet_id` | str | - | ID подсети (обязательно) |
| `image_id` | str | - | ID образа (если не указан - используется `image_family`) |
| `image_family` | str | `rocky-10` | Семейство образов |
| `cores` | int | `2` | Количество vCPU |
| `memory` | int | `2` | Объём RAM в ГБ |
| `core_fraction` | int | `20` | Базовая производительность CPU: `20`, `50`, `100` |
| `disk_size` | int | `10` | Размер загрузочного диска в ГБ |
| `disk_type` | str | `network-hdd` | Тип диска: `network-hdd`, `network-ssd`, `network-ssd-nonreplicated` |
| `platform_id` | str | `standard-v3` | Платформа ВМ |
| `assign_public_ip` | bool | `true` | Назначать публичный IP |
| `preemptible` | bool | `true` | Прерываемая ВМ (до 24 часов) |
| `username` | str | `alex` | Пользователь, создаваемый через cloud-init |
| `ssh_key` | str | - | Публичный SSH-ключ (обязательно) |
| `state` | str | `present` | `present` или `absent` |

#### Возвращаемые значения

```json
{
  "vm": {
    "id": "epdxxxxxxxxxxxxxxxx",
    "name": "berko-rocky-vm",
    "zone": "ru-central1-a",
    "status": "RUNNING",
    "preemptible": true,
    "internal_ip": "x.x.x.x",
    "external_ip": "x.x.x.x"
  }
}
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

### Роль `clickhouse`

Роль основана на [AlexeySetevoi/ansible-clickhouse](https://github.com/AlexeySetevoi/ansible-clickhouse) версии `1.13`. В процессе использования потребовалась модификация задачи установки пакетов.

#### Причина модификации

ClickHouse **намеренно не подписывает RPM-пакеты** - подписываются только метаданные репозитория (`repomd.xml`). При установке через модуль `dnf` Ansible проверяет подпись самого пакета и падает с ошибкой:

```
Failed to validate GPG signature for clickhouse-server-XX.X.X.XX-1.noarch:
Package clickhouse-server-XX.X.X.XX.noarch.rpm is not signed
```

#### Что изменено

В файле `roles/clickhouse/tasks/install/dnf.yml` задача установки пакетов переопределена:

```yaml
- name: Install by YUM | Ensure clickhouse package installed (version {{ clickhouse_version }})
  dnf:
    name: "{{ clickhouse_package | map('regex_replace', '$', '-' + clickhouse_version) | list }}"
    state: present
    disable_gpg_check: "true"
  become: true
  tags: [install]
  when: clickhouse_version != 'latest'
```

Ключевое отличие от оригинальной роли - параметр **`disable_gpg_check: "true"`**, который передаётся напрямую в модуль `dnf`. Это официально поддерживаемый параметр, который отключает валидацию подписи пакета.

#### Пример использования

```yaml
- name: Install ClickHouse
  hosts: clickhouse
  become: true
  gather_facts: true

  roles:
    - role: my_own_namespace.yandex_cloud_elk.clickhouse
      vars:
        clickhouse_version: "22.3.3.44"
        clickhouse_packages:
          - clickhouse-client
          - clickhouse-server
          - clickhouse-common-static
        clickhouse_repo_key: "https://packages.clickhouse.com/rpm/lts/repodata/repomd.xml.key"
```

## Лицензия

MIT

## Автор

Berko Alex (@AlexBerko)