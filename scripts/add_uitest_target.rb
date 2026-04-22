#!/usr/bin/env ruby
# Adds NORMALIZERUITests target to the NORMALIZER.xcodeproj.
# Idempotent: bails early if the target already exists.

$LOAD_PATH.unshift(*Dir.glob(File.expand_path("~/.gem/ruby/*/gems/*/lib")))
require "xcodeproj"

PROJECT_PATH = File.expand_path(
  "../ios/NORMALIZER/NORMALIZER.xcodeproj",
  File.dirname(File.expand_path(__FILE__))
)
TARGET_NAME = "NORMALIZERUITests"
TEST_DIR = File.expand_path(
  "../ios/NORMALIZER/NORMALIZERUITests",
  File.dirname(File.expand_path(__FILE__))
)

project = Xcodeproj::Project.open(PROJECT_PATH)

if project.targets.any? { |t| t.name == TARGET_NAME }
  puts "Target #{TARGET_NAME} already exists — nothing to do."
  exit 0
end

app_target = project.targets.find { |t| t.name == "NORMALIZER" }
raise "App target not found" unless app_target

test_target = project.new_target(
  :ui_test_bundle,
  TARGET_NAME,
  :ios,
  "18.0",
  nil,
  :swift
)

# Make UI test target depend on app and point at app as test host / target.
test_target.add_dependency(app_target)

test_target.build_configurations.each do |config|
  config.build_settings["TEST_TARGET_NAME"] = "NORMALIZER"
  config.build_settings["PRODUCT_BUNDLE_IDENTIFIER"] = "com.normalizer.app.uitests"
  config.build_settings["SWIFT_VERSION"] = "6.0"
  config.build_settings["IPHONEOS_DEPLOYMENT_TARGET"] = "18.0"
  config.build_settings["TARGETED_DEVICE_FAMILY"] = "1,2"
  config.build_settings["GENERATE_INFOPLIST_FILE"] = "YES"
  config.build_settings["CODE_SIGN_STYLE"] = "Automatic"
  config.build_settings["ALWAYS_EMBED_SWIFT_STANDARD_LIBRARIES"] = "YES"
  config.build_settings["LD_RUNPATH_SEARCH_PATHS"] = [
    "$(inherited)",
    "@executable_path/Frameworks",
    "@loader_path/Frameworks"
  ]
end

# Group + file references for test sources.
group = project.main_group.find_subpath(TARGET_NAME, true)
group.set_source_tree("<group>")
group.set_path(TARGET_NAME)

Dir.glob("#{TEST_DIR}/*.swift").sort.each do |swift_path|
  file_ref = group.new_reference(File.basename(swift_path))
  test_target.source_build_phase.add_file_reference(file_ref)
end

# Create a shared scheme so xcodebuild -scheme works.
schemes_dir = File.join(PROJECT_PATH, "xcshareddata", "xcschemes")
FileUtils.mkdir_p(schemes_dir)

project.save

# Build & share the scheme using Xcodeproj's scheme helper.
scheme = Xcodeproj::XCScheme.new
scheme.configure_with_targets(app_target, test_target)
scheme.add_test_target(test_target)
scheme.save_as(PROJECT_PATH, "NORMALIZER", true)

puts "Added #{TARGET_NAME} target and shared scheme."
