#! /usr/bin/env python3
import os, sys, time 

sys.path.append('/home/onie/sde/bf-sde-9.11.0/install/lib/python3.8/site-packages/tofino/')
sys.path.append('/home/onie/sde/bf-sde-9.11.0/install/lib/python3.8/site-packages/tofino/bfrt_grpc/')

os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "1"
# os.environ["GRPC_POLL_STRATEGY"] = "poll"
# os.environ["GRPC_VERBOSITY"] = "debug"

import bfrt_grpc.client as gc


class BfRt_interface():

    def __init__(self, dev, grpc_addr, client_id):
        self.dev_tgt = gc.Target(dev, pipe_id=0xFFFF)
        self.bfrt_info = None

        self.interface = gc.ClientInterface(grpc_addr, client_id=client_id,
                    device_id=dev, notifications=None)
        self.bfrt_info = self.interface.bfrt_info_get()
        self.p4_name = self.bfrt_info.p4_name_get()

        self.interface.bind_pipeline_config(self.p4_name)

        self.learn_filter = self.bfrt_info.learn_get("digest")
        self.learn_filter.info.data_field_annotation_add("src_addr", "ipv4")

        self.total_received = 0
        self.recievedDigest = 0
        self.digestList = []
        self.missedDigest = 0

        print("Connected to Device: {}, Program: {}, ClientId: {}".format(
                dev, self.p4_name, client_id))


    def list_tables(self):
            for key in sorted(self.bfrt_info.table_dict.keys()):
                print(key)

    def print_table_info(self, table_name):
            print("====Table Info===")
            t = self.bfrt_info.table_get(table_name)
            print("{:<30}: {}".format("TableName", t.info.name_get()))
            print("{:<30}: {}".format("Size", t.info.size_get()))
            print("{:<30}: {}".format("Actions", t.info.action_name_list_get()))
            print("{:<30}:".format("KeyFields"))
            for field in sorted(t.info.key_field_name_list_get()):
                print("  {:<28}: {} => {}".format(field, t.info.key_field_type_get(field), t.info.key_field_match_type_get(field)))
            print("{:<30}:".format("DataFields"))
            for field in t.info.data_field_name_list_get():
                print("  {:<28}: {} {}".format(
                    "{} ({})".format(field, t.info.data_field_id_get(field)), 
                    # type(t.info.data_field_allowed_choices_get(field)), 
                    t.info.data_field_type_get(field),
                    t.info.data_field_size_get(field),
                    ))
            print("================")

    def _read_digest(self):
        self.isRunning = True
        while self.isRunning:
            try:
                digest = self.interface.digest_get(0.1)
                data_list = self.learn_filter.make_data_list(digest)
                self.total_received += len(data_list)
                self.digestList.append(data_list)

                self.recievedDigest += 1
                if self.recievedDigest % 1000 == 0:
                    print(f"Received {self.recievedDigest} digests")

                self.hasFirstData = True
            except Exception as err:
                self.missedDigest += 1
                print(f"error reading digest {self.missedDigest}, {err} ", end="", flush=True)
                if self.hasFirstData and self.missedDigest >= 3:
                    self.isRunning = False
                    print("")
                time.sleep(0.05)

    def run(self):
        self._read_digest()


def main():
    bfrt_interface = BfRt_interface(0, 'localhost:50052', 0)
    bfrt_interface.list_tables()


    while True:
        bfrt_interface.run()

if __name__ == "__main__":
    main()
