import argparse
import paramiko
import subprocess

def setup_ssh_client(ip, password, port):
    # setup ssh client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, port=port, username='root', password=password, look_for_keys=False, allow_agent=False)
    return client

def get_public_key(client):
    # 得到公开密钥
    stdin, stdout, stderr = client.exec_command('cat ~/.ssh/id_rsa.pub')
    public_key = stdout.read().decode('utf-8').strip()
    return public_key

def distribute_public_key(client, public_key):
    # do distribute public key
    stdin, stdout, stderr = client.exec_command(f'echo "{public_key}" >> ~/.ssh/authorized_keys')
    exit_status = stdout.channel.recv_exit_status()  # Wait for the command to complete
    if exit_status == 0:
        return 0, stdout.read().decode('utf-8').strip()
    else:
        return exit_status, stderr.read().decode('utf-8').strip()

def get_host_fingerprint(ip, port):
    try:
        # 使用 ssh-keyscan 获取主机指纹
        result = subprocess.run(['ssh-keyscan', '-p', str(port), ip], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            print(f'Failed to get fingerprint for {ip}')
            return None
    except Exception as e:
        # 错误处理
        print(f'Error getting fingerprint for {ip}: {e}')
        return None

def add_fingerprint_to_remote_known_hosts(client, fingerprint):
    # 向远程已知主机添加信息
    try:
        stdin, stdout, stderr = client.exec_command(f'echo "{fingerprint}" >> ~/.ssh/known_hosts')
        exit_status = stdout.channel.recv_exit_status()  # Wait for the command to complete
        if exit_status == 0:
            print('Fingerprint added to remote known_hosts')
        else:
            print(f'Failed to add fingerprint to remote known_hosts: {stderr.read().decode("utf-8").strip()}')
    except Exception as e:
        # 错误处理
        print(f'Error adding fingerprint to remote known_hosts: {e}')

def config_nodes_mianmi(nodes, port, password):
    # config nodes 免密
    public_keys = {}
    fingerprints = {}

    for node in nodes:
        client = setup_ssh_client(node, password, port)
        stdin, stdout, stderr = client.exec_command(
            'if [ ! -f ~/.ssh/id_rsa ]; then ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa; fi')
        public_keys[node] = get_public_key(client)
        fingerprints[node] = get_host_fingerprint(node, port)

        stdout.channel.recv_exit_status()  # Wait for the command to complete
        client.close()

    for node in nodes:
        client = setup_ssh_client(node, password, port)
        for ip, public_key in public_keys.items():
            exit_status, msg = distribute_public_key(client, public_key)
            print('distribute_public_key ', ip, 'result: ', exit_status, msg)
        for ip, fingerprint in fingerprints.items():
            if fingerprint:
                add_fingerprint_to_remote_known_hosts(client, fingerprint)
        client.close()

def main():
    parser = argparse.ArgumentParser(description='SSH Key Distributor')
    parser.add_argument('--ips', help='Comma-separated list of IP addresses', required=True)
    parser.add_argument('--password', default='hunyuan123', help='Root password for all machines')
    parser.add_argument('--port', type=int, default=56000, help='SSH port for all machines')

    args = parser.parse_args()

    ip_list = args.ips.split(',')

    machines = [{'ip': ip.strip(), 'password': args.password, 'port': args.port} for ip in ip_list]
    print('machines: ', machines)

    # Generate SSH keys on all machines if not already present
    for machine in machines:
        client = setup_ssh_client(machine['ip'], machine['password'], machine['port'])
        stdin, stdout, stderr = client.exec_command(
            'if [ ! -f ~/.ssh/id_rsa ]; then ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa; fi')
        stdout.channel.recv_exit_status()  # Wait for the command to complete
        client.close()

    # Collect public keys from all machines
    public_keys = {}
    for machine in machines:
        client = setup_ssh_client(machine['ip'], machine['password'], machine['port'])
        public_keys[machine['ip']] = get_public_key(client)
        client.close()
    print('public_keys: ', public_keys)

    # Collect fingerprints from all machines
    fingerprints = {}
    for machine in machines:
        fingerprints[machine['ip']] = get_host_fingerprint(machine['ip'], machine['port'])
    print('fingerprints: ', fingerprints)

    # Distribute all public keys and fingerprints to all machines
    for machine in machines:
        client = setup_ssh_client(machine['ip'], machine['password'], machine['port'])
        for ip, public_key in public_keys.items():
            exit_status, msg = distribute_public_key(client, public_key)
            print('distribute_public_key ', ip, 'result: ', exit_status, msg)
        for ip, fingerprint in fingerprints.items():
            if fingerprint:
                add_fingerprint_to_remote_known_hosts(client, fingerprint)
        client.close()

    # 配置免密成功
    print("SSH keys and fingerprints have been distributed successfully.")

if __name__ == '__main__':
    main()
