set(MODULE_NAME SymmetryPlaneFromPoints)
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  ${MODULE_NAME}Logic.py
  logic/__init__.py
  logic/utils.py
  logic/plane.py
  logic/gonion.py
  logic/sheet.py
  logic/split.py
  logic/guide.py
  logic/export.py
  logic/mandible.py
)
set(MODULE_PYTHON_RESOURCES
  Resources/UI/${MODULE_NAME}.ui
)
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
)
if(BUILD_TESTING)
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)
  add_subdirectory(Testing)
endif()
