from pioneer.common import clouds, peak_detector
from pioneer.common.platform import parse_datasource_name
from pioneer.common.trace_processing import TraceProcessingCollection, Desaturate, RemoveStaticNoise, ZeroBaseline, Smooth
from pioneer.das.api.datasources.virtual_datasources.virtual_datasource import VirtualDatasource

from pioneer.das.api.samples import Echo, FastTrace

from typing import Any

import copy
import numpy as np

class Echoes_from_Traces(VirtualDatasource):

    def __init__(self, ds_type, trr_ds_name, sensor=None, nb_detections_max:int=3):
        super(Echoes_from_Traces, self).__init__(ds_type, [trr_ds_name], None)
        self.ds_type = ds_type
        self.trr_ds_name = trr_ds_name
        self.sensor = sensor
        self.nb_detections_max = nb_detections_max
        self.peak_detector = peak_detector.PeakDetector(nb_detections_max=self.nb_detections_max)
        self.amplitude_scaling = 1

        self.trace_processing = TraceProcessingCollection([
              Desaturate(self.sensor.saturation_calibration),
              RemoveStaticNoise(self.sensor.static_noise),
              ZeroBaseline(),
              Smooth(),
            ])


    @staticmethod
    def add_all_combinations_to_platform(pf:'Platform', nb_detections_max:int=3) -> list:
        try:
            trr_dss = pf.expand_wildcards(["*_trr*","*_ftrr*"]) # look for all leddar with traces
            virtual_ds_list = []

            for trr_ds_name_full_name in trr_dss:
                
                trr_ds_name, trr_pos, ds_type = parse_datasource_name(trr_ds_name_full_name)
                sensor = pf[f"{trr_ds_name}_{trr_pos}"]
                virtual_ds_type = f"ech-{ds_type}"

                try:
                    vds = Echoes_from_Traces(
                            ds_type = virtual_ds_type,
                            trr_ds_name = trr_ds_name_full_name,
                            sensor = sensor,
                            nb_detections_max = nb_detections_max,
                    )
                    sensor.add_virtual_datasource(vds)
                    virtual_ds_list.append(f"{trr_ds_name}_{trr_pos}_{virtual_ds_type}")
                except Exception as e:
                    print(e)
                    print(f"vitual datasource {trr_ds_name}_{trr_pos}_{virtual_ds_type} was not added")
                
            return virtual_ds_list
        except Exception as e:
            print(e)
            print("Issue during try to add virtual datasources Echoes_from_Traces.")


    def initialize_local_cache(self, data):
        self.local_cache = copy.deepcopy(data)


    def get_echoes(self, processed_traces):
        try:
            data = processed_traces
            self.local_cache['data'][...] = data['data']
            self.local_cache['time_base_delays'][...] = data['time_base_delays']
            self.local_cache['distance_scaling'][...] = data['distance_scaling']
        except:
            self.initialize_local_cache(processed_traces)

        traces = {'data': self.local_cache['data'], 
                  'time_base_delays': self.local_cache['time_base_delays'],
                  'distance_scaling': self.local_cache['distance_scaling']}

        echoes = self.peak_detector(traces)
        echoes['amplitudes'] *= self.amplitude_scaling

        additionnal_fields = {}
        for key in echoes:
            if key not in ['indices','distances','amplitudes','timestamps','flags']:
                additionnal_fields[key] = [echoes[key], 'f4']
        return echoes, additionnal_fields


    def get_echoes_from_fast_traces(self, processed_fast_traces):
        # TODO: improve merging by replacing the saturated lines and columns
        echoes_high, additionnal_fields_high = self.get_echoes(processed_fast_traces[self.sensor.FastTraceType.MidRange])
        echoes_low, additionnal_fields_low = self.get_echoes(processed_fast_traces[self.sensor.FastTraceType.LowRange])
        echoes = {}
        for field in ['indices','distances','amplitudes']:
            echoes[field] = np.hstack([echoes_high[field], echoes_low[field]])
        additionnal_fields = {}
        for field in additionnal_fields_high:
            if field not in ['indices','distances','amplitudes']:
                additionnal_fields[field] = [np.hstack([additionnal_fields_high[field][0], additionnal_fields_low[field][0]])
                                            , additionnal_fields_high[field][1]]
        return echoes, additionnal_fields


    def get_at_timestamp(self, timestamp):
        sample = self.datasources[self.trr_ds_name].get_at_timestamp(timestamp)
        return self[int(np.round(sample.index))]


    def __getitem__(self, key:Any):
        #Load data in local cache to prevent modifying the original data
        trace_sample = self.datasources[self.trr_ds_name][key]
        timestamp = trace_sample.timestamp
        specs = trace_sample.specs
        if isinstance(trace_sample, FastTrace):
            get_echoes = self.get_echoes_from_fast_traces
        else:
            get_echoes = self.get_echoes

        processed_traces = trace_sample.processed(self.trace_processing)
        echoes, additionnal_fields = get_echoes(processed_traces)

        raw = clouds.to_echo_package(
            indices = np.array(echoes['indices'], 'u4'), 
            distances = np.array(echoes['distances'], 'f4'), 
            amplitudes = np.array(echoes['amplitudes'], 'f4'),
            additionnal_fields = additionnal_fields,
            timestamps = None, 
            flags = None, 
            timestamp = timestamp,
            specs = {"v" : specs['v'], "h" : specs['h'], "v_fov" : specs['v_fov'], "h_fov" : specs['h_fov']},
            distance_scale = 1.0, 
            amplitude_scale = 1.0, 
            led_power = 1.0, 
            eof_timestamp = None)
        
        return Echo(trace_sample.index, self, virtual_raw = raw, virtual_ts = timestamp)
