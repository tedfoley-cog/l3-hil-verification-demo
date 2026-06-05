@ASIL-C @REQ-SYS-AEB-002 @domain-ADAS
Feature: AEB deceleration profile and warning coordination

  Decomposed from REQ-SYS-AEB-002 into 4 atomic scenarios.

  @decomposed-1
  Scenario: AEB deceleration profile and warning coordination — deceleration
    Given the host vehicle is travelling at 30 kph
    Given a target vehicle is detected ahead
    When the AEB brake command is initiated
    Then apply a minimum deceleration of 6 m/s^2 within 500 ms of brake command initiation when the host vehicle is travelling be

  @decomposed-2
  Scenario: AEB deceleration profile and warning coordination — warning
    Given the system is in normal operating mode
    When a forward collision threat is detected
    Then illuminate the instrument cluster warning lamp within 200 ms of threat detection

  @decomposed-3
  Scenario: AEB deceleration profile and warning coordination — warning
    Given the system is in normal operating mode
    When a forward collision threat is detected
    Then activate simultaneously with the visual warning

  @decomposed-4
  Scenario: AEB deceleration profile and warning coordination — deceleration
    Given the system is in normal operating mode
    When the AEB brake command is initiated
    Then ramp to full braking (>= 9
