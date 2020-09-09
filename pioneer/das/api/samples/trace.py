from pioneer.das.api.samples.sample import Sample

from typing import Callable

import copy
import numpy as np

class Trace(Sample):
    def __init__(self, index, datasource, virtual_raw = None, virtual_ts = None):
        super(Trace, self).__init__(index, datasource, virtual_raw, virtual_ts)
    
    @property
    def raw(self):
        if self._raw is None:
            self._raw = super(Trace, self).raw
            
            self._raw['time_base_delays'] = self.datasource.sensor.time_base_delays
            self._raw['distance_scaling'] = self.datasource.sensor.distance_scaling
            self._raw['trace_smoothing_kernel'] = self.datasource.sensor.get_trace_smoothing_kernel()

        return self._raw

    @property
    def specs(self):
        # override the sensor specs if they are present in the YAML config file
        sensor_specs = self.datasource.sensor.specs
        if sensor_specs is not None:
            return sensor_specs
        return {k: self.raw[k] for k in ['v', 'h', 'v_fov', 'h_fov']}

    @property
    def timestamps(self):
        return self.raw['t']

    def processed(self, trace_processing:Callable):
        raw_copy = copy.deepcopy(self.raw)
        processed_traces = trace_processing(raw_copy)
        return processed_traces

    @staticmethod
    def saturation_flags(traces):
        flags = np.zeros(traces['data'].shape[0], dtype='u2')

        traces['data'] = traces['data'].astype('float64')
        saturation_value = traces['data'].max()
        if saturation_value == 0:
            return traces

        where_plateau = np.where(traces['data'] == saturation_value)
        channels, ind, sizes = np.unique(where_plateau[0], return_index=True, return_counts=True)
        positions = where_plateau[1][ind]

        for channel, position, size in zip(channels, positions, sizes):
            if size > 5 and position > 2 and position + size + 2 < traces['data'].shape[-1]:
                flags[channel] = 1
        return flags