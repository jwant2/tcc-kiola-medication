# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

## [0.6.0](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.5.2...v0.6.0) (2021-05-18)


### Features

* put the default meds at the front of the query results ([607f700](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/607f70057d76dff3c02da6ca428b15ff1b074e12))

### [0.5.2](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.5.1...v0.5.2) (2021-05-03)


### Bug Fixes

* fixed med observation data can not be queried via API ([1c57925](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/1c579256620034397413dd8b48eab6f906b6e4c8))

### [0.5.1](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.5.0...v0.5.1) (2021-04-29)


### Bug Fixes

* **tcc-medications:** schedule text is hard to understand ([125f5c7](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/125f5c7c0540bce00ff2224f3034d8d96c022b69))
* **tcc-medications:** schedule text is hard to understand ([3e4389a](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/3e4389a0acbb82a2fecc9f622f2151279f199f41))

## [0.5.0](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.4.3-dev.2...v0.5.0) (2021-04-26)


### Features

* add new fields to med obs ([898d3e7](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/898d3e74bcc43ffb5dda380e1bbdccce8f122fe7))
* implement medication reminder push notification ([3e81e77](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/3e81e77de1b57d973baa4d7a252f4ade9f49ea6e))


### Bug Fixes

* fix med chart not rendering due to invalid obs ([fe59327](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/fe593273442f69a69afeaa7390be9a27641113a3))
* **tcc-medications:** edit schedule not working ([804ee6d](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/804ee6d9342d90e2c99bb9ca059ed966f5679621)), closes [#214](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/issues/214)

### [0.4.3-dev.2](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.4.3-dev.1...v0.4.3-dev.2) (2021-04-20)


### Bug Fixes

* fixed endDate:null for schedule query api not handled properly. ([1b4fc69](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/1b4fc6941e46b0c04a6c86c219c195a1b3a6d9b4))

### [0.4.3-dev.1](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.4.3-dev.0...v0.4.3-dev.1) (2021-04-06)


### Features

* add date query to schedule endpoint ([ae1f4e2](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/ae1f4e21bb3e766727d34ea5e7b7a74342569951))
* add startDate and endDate query params to schedule query api ([a7044c0](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/a7044c0f88205d081e283c0020a49b15b3fe1c86))

### [0.4.3-dev.0](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.4.2...v0.4.3-dev.0) (2021-03-22)


### Features

* implement generic mos data parser: ([e7d227f](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/e7d227f3ca3d5a1b8e416ebb3bb50831c9e12f4c))


### Bug Fixes

* removed duplicate changelog.md and update test codes ([0284e5f](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/0284e5f97352bd509687f13a21b9f2d76fd2c3fe))
* temporary disable fomulation filed for schedule api ([e4e9676](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/e4e9676c152157cdd15d9b11b4183d887aa0b73e))

### [0.4.2](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.4.1...v0.4.2) (2021-02-25)


### Bug Fixes

* fixed changelog and version ([0ec092c](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/0ec092c40bdb007008cff2ed0c5891a5bbe4b200))

### [0.4.1](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.4.0...v0.4.1) (2021-02-25)


### Bug Fixes

* fixed request data validation ([e53df63](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/e53df6324ca8ca33432e294ab1bd8019f4fb2593))

## [0.4.0](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.3.3...v0.4.0) (2021-02-24)


### Features

* add schedule update to PUT user_preference api. fix actual query filtering ([abbc961](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/abbc9615f5a92f06222c3de9ebeadbc9fd984ac7))

### [0.3.3](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.3.2...v0.3.3) (2021-02-22)


### Bug Fixes

* fix schedule display format ([c99b2bf](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/c99b2bf0677e3836a4c7d11246fce3500f262a22))

### [0.3.2](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.3.1...v0.3.2) (2021-02-17)


### Bug Fixes

* remove searching limit for compound api ([9c99be5](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/9c99be560f9d281a8d0b7d1beee233d35e62dc88))

### [0.3.1](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.3.0...v0.3.1) (2021-02-16)


### Bug Fixes

* fix constant FORTNIGHTLY and schedule display format ([7e99591](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/7e99591e3c486c11759af886e192d7188e467b61))

## [0.3.0](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.2.5...v0.3.0) (2021-01-25)


### Features

* improve user_preference api. ([40d2968](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/40d2968d63b8b6115692c326db5d207c2d0ad0d0))

### [0.2.5](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.2.4...v0.2.5) (2021-01-22)


### Bug Fixes

* add medicationType to compound response ([6bcb4e0](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/6bcb4e08eafd044f658736c8b6c2687bcf37969e))

### [0.2.4](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.2.3...v0.2.4) (2021-01-14)


### Bug Fixes

* fix bugs with reaction api ([a3ea48b](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/a3ea48bf7cb926b534fb04e40713221fdb0030b1))

### [0.2.3](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.2.2...v0.2.3) (2021-01-14)


### Bug Fixes

* fix bugs with patient created compounds ([280f89f](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/280f89f255cdf86a8567a6625291f8f15cf67e1c))

### [0.2.2](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.2.1...v0.2.2) (2021-01-14)


### Bug Fixes

* fix uid generation for patient defined compounds ([86a003b](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/86a003baff88dbda9fc6d3d07f8fa8d027fcae00))

### [0.2.1](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.2.0...v0.2.1) (2021-01-14)


### Bug Fixes

* disable prescription listener for Kiola's medication observation profile. fix permission issue with prescription PUT api. fix result counter of change histroy api. ([6bc2b8c](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/6bc2b8c4bd798d4c692df030092a97582c9257e7))

## [0.2.0](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.1.3...v0.2.0) (2021-01-13)


### Features

* add PUT/DELETE request for updating/deleting resources. modify reaction resource request body ([d32681b](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/d32681b884c6c6f59b0d3184cb6351b5ec8f0e28))

### [0.1.3](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.1.2...v0.1.3) (2021-01-08)


### Features

* add management command for medication import ([e7326ea](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/e7326ea946feebf40ece7b8d193f744cc0f4bcfa))


### Bug Fixes

* update api response data format ([01e6ee6](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/01e6ee6efb15f67f7631437d035906b06b81e5b3))

### [0.1.2](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.1.1...v0.1.2) (2020-12-17)


### Bug Fixes

* remove pbs import migration ([93f7404](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/93f7404516a84121053d005f321b81f20ecb4c94))

### [0.1.1](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/compare/v0.1.0...v0.1.1) (2020-12-17)


### Features

* add api for patient defined compound ([8ae797e](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/8ae797e12206f823475c3b6ad0a18ceab88235ed))
* add chart for medication observation ([88b6217](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/88b621762c3c7ef9282dcf1cee023a8044206a8d))
* add migration code for pbs import ([e64c1ad](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/e64c1adb6156ef85c1304446de1378cf3377d9b9))


### Bug Fixes

* optimise medication import via moving compound creation to prescription creation. ([c17da85](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/c17da8545e9c5a82aa09e216c746022b60984cdd))

## 0.1.0 (2020-12-14)


### Features

* add histroy api for prescription ([f280012](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/f280012741beecf6c24a0f6d30609e67fdbb66c5))
* add med observation profile ([65952e9](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/65952e93ed438f6490ff0418dfb491faf6e73e81))
* add swagger doc codes and changes to serializers ([e812ca1](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/e812ca14f02ec3ac5a98b44b3178daed658a48a0))
* add test codes ([7d282d9](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/7d282d99b68aa7e8308c8dfab0762b840fee6cae))
* added compound seearch api, move apis to api_urls and add swagger codes ([6015b89](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/6015b89b89b46314993f0b532e9ccca87a91c8a7))
* added models and api views for adverse reaction ([7a05e42](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/7a05e42a630978b51a3c1bd02b7d45b79c99d420))
* added models and apis for prescritions, scheduledTaking and user pref. ([9846155](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/9846155fafe7b4e713152f9797d130a8eccfaec7))
* added prescription profiles automation and med profile query api ([f211ffc](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/f211ffcde453fe31ea2a9050045019c33cc2c6c5))
* modify prescription pages and forms. add/replace api endpoints for changes to prescription pages ([0cb81c3](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/0cb81c3bfafa73a9ca4efe440df569b8bdceaed0))
* move compound import to admin view ([518e99e](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/518e99e14c425aff9ca3176ff9eaf9dc88b615c0))
* update api and its docs to meet changes on mobile app ([559ea7b](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/559ea7bfc6bc1b5239c5c4e785bf007e448b64c8))


### Bug Fixes

* fix swagger codes ([1b3ac93](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/1b3ac93b29a19157ea87b8ea63be7e0b357c4ad5))
* fix updating displayable_taking for prescription. fix generating takingunit during compound imports ([391407e](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/391407e9d302422c3fd25e30f7843e1f5494071c))
* moved add urls for handling single resource ([98ddc0a](https://bitbucket.org/teleclinicalcare/tcc-kiola-medication/commit/98ddc0abd944e67b04e8d96e7eef0a66833db60e))
