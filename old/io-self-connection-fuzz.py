from runner import *
import os
import shutil
import queue
import threading

BASE_DIR = '/home/rqou/.local/share/lxc/altera-quartus-prime-lite-18/rootfs/home/rqou'

QSF_TMPL = """set_global_assignment -name FAMILY "MAX V"
set_global_assignment -name DEVICE 5M240ZT100C4
set_global_assignment -name TOP_LEVEL_ENTITY maxvtest
set_global_assignment -name ORIGINAL_QUARTUS_VERSION 18.0.0
set_global_assignment -name PROJECT_CREATION_TIME_DATE "03:45:37  MAY 30, 2018"
set_global_assignment -name LAST_QUARTUS_VERSION "18.0.0 Lite Edition"
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name ERROR_CHECK_FREQUENCY_DIVISOR "-1"
set_global_assignment -name EDA_SIMULATION_TOOL "ModelSim-Altera (Verilog)"
set_global_assignment -name EDA_TIME_SCALE "1 ps" -section_id eda_simulation
set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation
set_global_assignment -name VERILOG_FILE top.v
set_global_assignment -name NUM_PARALLEL_PROCESSORS 1
set_global_assignment -name INCREMENTAL_COMPILATION OFF
set_global_assignment -name ROUTING_BACK_ANNOTATION_FILE maxvtest.rcf

set_location_assignment IOC_X{}_Y{}_N{} -to a
set_location_assignment IOC_X{}_Y{}_N{} -to o
"""

RCF_TMPL = """signal_name = a {{
    IO_DATAIN:*;
    LOCAL_INTERCONNECT:X{}Y{}S0I{};
    IO_DATAOUT:*;
    dest = ( o, DATAIN );
}}
"""

NTHREADS = 20

def fuzz_lut_at(workdir, threadi, srcx, srcy, srcn, dstI):
    if srcn == 0:
        otherlutN = 1
    else:
        otherlutN = 0

    with open(workdir + '/maxvtest.qsf', 'w') as f:
        f.write(QSF_TMPL.format(srcx, srcy, srcn, srcx, srcy, otherlutN))

    with open(workdir + '/maxvtest.rcf', 'w') as f:
        f.write(RCF_TMPL.format(srcx, srcy, dstI))

    while True:
        try:
            run_one_flow("io-self-connection/thread{}".format(threadi), False, True, False)
            break
        except Exception:
            pass

    shutil.copy(workdir + '/output_files/maxvtest.pof', 'io-self-connection/ioself_X{}_Y{}_N{}_to_Local{}.pof'.format(srcx, srcy, srcn, dstI))
    shutil.copy(workdir + '/maxvtest.rcf', 'io-self-connection/ioself_X{}_Y{}_N{}_to_Local{}.rcf'.format(srcx, srcy, srcn, dstI))

def main():
    os.mkdir(BASE_DIR + '/io-self-connection')

    workqueue = queue.Queue()
    donequeue = queue.Queue()

    num_items = 0
    for srcx in [1, 8]:
        for srcy in [1, 2, 3, 4]:
            if srcx == 1 or srcy == 2:
                N = 4
            else:
                N = 5

            for srcn in range(N):
                for dstI in range(18):
                    workqueue.put((srcx, srcy, srcn, dstI))
                    num_items += 1

    def threadfn(threadi):
        MYDIR = BASE_DIR + '/io-self-connection/thread{}'.format(threadi)
        shutil.copytree(BASE_DIR + '/io-self-connection-seed', MYDIR)

        while True:
            try:
                srcx, srcy, srcn, dstI = workqueue.get(timeout=0)
            except queue.Empty:
                return

            print("Working on X{}_Y{}_N{} -> Local{}".format(srcx, srcy, srcn, dstI))
            fuzz_lut_at(MYDIR, threadi, srcx, srcy, srcn, dstI)
            donequeue.put((srcx, srcy, srcn, dstI))

    for threadi in range(NTHREADS):
        t = threading.Thread(target=threadfn, args=(threadi,))
        t.start()

    while num_items:
        srcx, srcy, srcn, dstI = donequeue.get()
        print("Finished X{}_Y{}_N{} -> Local{}".format(srcx, srcy, srcn, dstI))
        num_items -= 1

if __name__=='__main__':
    main()
