package com.industrialdigitaltwin.flink;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class GpsEvent {
    public String id;
    public String unit_id;
    public String timestamp;
    public double latitude;
    public double longitude;
    public double speed;

    public GpsEvent() {}
}
