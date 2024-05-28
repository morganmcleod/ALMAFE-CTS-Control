import asyncio
from CTSDevices.Chopper.Band6Chopper import Chopper

async def main():
    print("Init...")
    c = Chopper()
    await asyncio.sleep(2)

    print("gotoCold...")
    c.gotoCold()
    await asyncio.sleep(2)

    print("gotoHot...")
    c.gotoHot()
    await asyncio.sleep(2)

    print("stop...")
    c.stop()

if __name__ == "__main__":
    asyncio.run(main())
