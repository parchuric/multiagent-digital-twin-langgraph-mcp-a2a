package com.industrialdigitaltwin.flink;

import org.apache.flink.api.common.functions.AggregateFunction;

public class MovingAverageAggregate implements AggregateFunction<ScadaEvent, MovingAverageAggregate.Accumulator, DeviceAvg> {
    public static class Accumulator {
        public double sum = 0;
        public long count = 0;
        public String deviceId = null;
        public String windowEnd = null;
    }

    @Override
    public Accumulator createAccumulator() {
        return new Accumulator();
    }

    @Override
    public Accumulator add(ScadaEvent value, Accumulator acc) {
        acc.sum += value.value;
        acc.count++;
        acc.deviceId = value.a_id;
        acc.windowEnd = value.timestamp;
        return acc;
    }

    @Override
    public DeviceAvg getResult(Accumulator acc) {
        DeviceAvg avg = new DeviceAvg();
        avg.deviceId = acc.deviceId;
        avg.windowEnd = acc.windowEnd;
        avg.avgValue = acc.count == 0 ? 0 : acc.sum / acc.count;
        return avg;
    }

    @Override
    public Accumulator merge(Accumulator a, Accumulator b) {
        a.sum += b.sum;
        a.count += b.count;
        return a;
    }
}

class DeviceAvg {
    public String deviceId;
    public String windowEnd;
    public double avgValue;
}
