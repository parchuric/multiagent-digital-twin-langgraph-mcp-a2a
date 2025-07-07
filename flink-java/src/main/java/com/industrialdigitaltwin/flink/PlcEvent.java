package com.industrialdigitaltwin.flink;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class PlcEvent {
    public String id;
    public String machine_id;
    public String timestamp;
    public int status_code;
    public double temperature;
    public double pressure;

    public PlcEvent() {}
}
