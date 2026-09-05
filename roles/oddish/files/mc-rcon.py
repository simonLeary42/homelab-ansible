#!/opt/minecraft/aio-mc-rcon/venv/bin/python
import sys, asyncio
from aiomcrcon import Client
async def main():
    assert not sys.stdin.isatty()
    password = sys.stdin.read().strip()
    assert len(sys.argv) == 2
    command = sys.argv[1]
    async with Client("127.0.0.1", 25575, password) as client:
        response = await client.send_cmd(command)
        print(response)
if __name__ == "__main__":
    asyncio.run(main())
