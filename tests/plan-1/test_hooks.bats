#!/usr/bin/env bats

@test "stop hook is executable and exits 0" {
  [ -x plugin/hooks/stop.sh ]
  run plugin/hooks/stop.sh
  [ "$status" -eq 0 ]
}

@test "post-iteration hook is executable and exits 0" {
  [ -x plugin/hooks/post-iteration.sh ]
  run plugin/hooks/post-iteration.sh
  [ "$status" -eq 0 ]
}
