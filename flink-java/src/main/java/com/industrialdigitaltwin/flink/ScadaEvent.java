package com.industrialdigitaltwin.flink;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ScadaEvent {
    public String id;
    public String a_id;
    public String timestamp;
    public double value;
    public String status;
    public String location;

    // Flink requires a public no-arg constructor
    public ScadaEvent() {}

    // Getters and setters are good practice, but Flink can also work with public fields
}
