test_role
=========

Тестовая роль для проверки работы модуля `my_own_module` из коллекции `my_own_namespace.yandex_cloud_elk`.

Role Variables
--------------

|vars|description|
|---|---|---|
| `path` | `/tmp/ansible_test/default.txt` | Path to the created fil.e |
| `content` | `Default content\n` | File content. |


Example Playbook
----------------

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

License
-------

MIT

Author Information
------------------

Berko Alex (@AlexBerko)
