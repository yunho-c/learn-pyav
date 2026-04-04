set shell := ["zsh", "-cu"]

module := "pyav_hwaccel_autoresearch.cli"

default:
    @just --list

install:
    pixi install

doctor:
    pixi run python -m {{module}} doctor

layout:
    pixi run python -m {{module}} layout

fixtures:
    pixi run python -m {{module}} fixtures list

resolutions:
    pixi run python -m {{module}} fixtures resolutions

suite-table path format="markdown":
    pixi run python -m {{module}} report suite-table {{path}} --format {{format}}

suite-graph path output="" dpi="160":
    output_path="{{output}}"; if [[ -n "$output_path" ]]; then pixi run python -m {{module}} report suite-graph {{path}} --output "$output_path" --dpi {{dpi}}; else pixi run python -m {{module}} report suite-graph {{path}} --dpi {{dpi}}; fi

lint:
    pixi run lint

format:
    pixi run format

typecheck:
    pixi run typecheck

test:
    pixi run test

check: format lint typecheck test

prepare fixture resolution="source" min_duration="30":
    pixi run python -m {{module}} fixtures prepare {{fixture}} --resolution {{resolution}} --min-duration-seconds {{min_duration}}

compare-decode fixture hwaccel="videotoolbox" resolution="source" min_duration="30" repeats="3" warmups="1":
    pixi run python -m {{module}} benchmark compare-decode {{fixture}} --hwaccel {{hwaccel}} --resolution {{resolution}} --min-duration-seconds {{min_duration}} --repeats {{repeats}} --warmups {{warmups}}

compare-encode fixture baseline candidate resolution="source" min_duration="30" repeats="3" warmups="1" bit_rate="4000000":
    pixi run python -m {{module}} benchmark compare-encode {{fixture}} --baseline-codec {{baseline}} --candidate-codec {{candidate}} --resolution {{resolution}} --min-duration-seconds {{min_duration}} --repeats {{repeats}} --warmups {{warmups}} --bit-rate {{bit_rate}}

compare-catalog resolution="source" min_duration="30" repeats="3" warmups="1" bit_rate="4000000":
    pixi run python -m {{module}} benchmark compare-all --resolution {{resolution}} --min-duration-seconds {{min_duration}} --repeats {{repeats}} --warmups {{warmups}} --bit-rate {{bit_rate}}

compare-fixture fixture resolution="source" min_duration="30" repeats="3" warmups="1" bit_rate="4000000":
    pixi run python -m {{module}} benchmark compare-all --fixture {{fixture}} --resolution {{resolution}} --min-duration-seconds {{min_duration}} --repeats {{repeats}} --warmups {{warmups}} --bit-rate {{bit_rate}}

compare-720p:
    just compare-catalog 720p 30

compare-1080p:
    just compare-catalog 1080p 30

compare-native:
    just compare-catalog source 30

compare-all:
    just compare-720p
    just compare-1080p
    just compare-native

compare-all-fast:
    just compare-catalog 720p 10 1 0
    just compare-catalog 1080p 10 1 0
    just compare-catalog source 10 1 0
