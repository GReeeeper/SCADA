import asyncio
import logging
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusDeviceContext

# Configure logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

async def run_server():
    # Define a simple datastore with initial values
    # Coils (co), Discrete Inputs (di), Holding Registers (hr), Input Registers (ir)
    store = ModbusDeviceContext(
        di=ModbusSequentialDataBlock(0, [0]*100),
        co=ModbusSequentialDataBlock(0, [0]*100),
        hr=ModbusSequentialDataBlock(0, [0]*100),
        ir=ModbusSequentialDataBlock(0, [0]*100)
    )
    
    # Create the server context
    context = ModbusServerContext(devices=store, single=True)

    print("[-] Factory Controller (PLC) Sim running on localhost:5020")
    print("[-] Data Store initialized (100 coils/registers)")

    # Background Physics Simulation
    async def physics_loop():
        import random
        # Initial State
        pressure = 50.0
        temp = 75.0
        
        while True:
            # 1. Read Coils (Controls)
            # Address 0-3 (We use 1=Override, 2=Valve, 3=Pump)
            # Note: start_address=0, count=5
            coils = context[0x00].getValues(1, 0, count=5)
            
            # Coil 1: Emergency Override (Kill Switch)
            override = coils[1] # Index 1 = Address 1? (Usually 1-based address maps to 0-based index if start=1... but we inited at 0)
            # ModbusSequentialDataBlock(0, ...) -> Index 0 is Address 0.
            # So Address 1 is Index 1.
            
            # Coil 3: Cooling Pump
            pump_on = coils[3] 
            
            if override:
                pressure = 0
                temp = 20
            else:
                # Physics Logic
                if pump_on:
                    # Cooling Active: Temp drops/stabilizes
                    if temp > 70: temp -= 0.5
                    elif temp < 70: temp += 0.2
                else:
                    # Cooling OFF: Temp Rises!
                    temp += 1.5
                    if temp > 120: temp = 120
                
                # Pressure fluctuation
                pressure += random.uniform(-1, 1)
                pressure = max(0, min(100, pressure))

            # 2. Update Holding Registers (10=Pres, 11=Temp)
            context[0x00].setValues(3, 10, [int(pressure)])
            context[0x00].setValues(3, 11, [int(temp)])
            
            # 3. Log Status occasionally
            if not pump_on and temp > 100:
                print(f"[!] ALERT: OVERHEATING! Temp: {int(temp)}C")
            
            await asyncio.sleep(1)

    # Start the TCP Server
    task = asyncio.create_task(physics_loop())
    await StartAsyncTcpServer(context, address=("localhost", 5020))

if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n[!] PLC Simulation Stopped.")
