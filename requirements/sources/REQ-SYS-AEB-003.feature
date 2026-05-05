# This requirement was authored directly as Gherkin by a feature engineer.
# It is already atomic and testable — Devin should validate it and pass
# it through to test generation without decomposition.

@REQ-SYS-AEB-003 @ASIL-B @domain-ADAS
Feature: Forward Collision Warning display timing

  The instrument cluster shall display the forward collision warning
  icon within 200 ms of the ADAS controller issuing a threat-detected
  signal, regardless of the current display page.

  Background:
    Given the host vehicle is travelling at <speed> kph
    And the ignition is in RUN state
    And the instrument cluster is powered and displaying the default page

  @stationary-target
  Scenario: FCW icon appears within 200 ms for stationary target approach
    Given a stationary target is detected at 80 m ahead
    When the ADAS controller issues a threat-detected signal
    Then the instrument cluster shall display the FCW warning icon
    And the display latency shall be less than 200 ms

  @moving-target
  Scenario: FCW icon appears within 200 ms for slower-moving target
    Given a target vehicle travelling at 20 kph is detected at 60 m ahead
    When the ADAS controller issues a threat-detected signal
    Then the instrument cluster shall display the FCW warning icon
    And the display latency shall be less than 200 ms
